/** @odoo-module */
const { Component } = owl;
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useRef, useState } from "@odoo/owl";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
const actionRegistry = registry.category("actions");

class DeferredExpenseReport extends owl.Component {
    setup() {
        super.setup(...arguments);
        this.initial_render = true;
        this.orm = useService('orm');
        this.action = useService('action');
        this.tbody = useRef('tbody');
        this.state = useState({
            account: null,
            account_data: null,
            account_data_list: null,
            account_total: null,
            total_deferred: null,
            total_recognized: null,
            total_remaining: null,
            total_current: null,
            total_not_started: null,
            total_before: null,
            total_later: null,
            currency: null,
            journals: null,
            selected_journal_list: [],
            analytics: null,
            selected_analytic_list: [],
            title: null,
            filter_applied: null,
            account_list: null,
            account_total_list: null,
            date_range: null,
            options: null,
            method: {
                'accrual': true
            },
            expandedAccounts: new Set(),
        });
        this.load_data();
    }

    formatNumberWithSeparators(number) {
        const parsedNumber = parseFloat(number);
        if (isNaN(parsedNumber)) {
            return "0.00";
        }
        return parsedNumber.toLocaleString('en-US', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    async load_data() {
        try {
            const action_title = this.props.action.display_name;

            // Load initial data for expense
            let filtered_data = await this.orm.call("deferred.report", "get_filter_values",
                [this.state.selected_journal_list, this.state.date_range, this.state.options,
                 this.state.selected_analytic_list, this.state.method, 'expense']);

            this.state.journals = filtered_data['journal_ids'];
            this.state.analytics = filtered_data['analytic_ids'];

            let account_data = await this.orm.call("deferred.report", "view_deferred_expense_report",
                [null, action_title]);

            this._processData(account_data);
            this.state.title = action_title;
        } catch (error) {
            console.error("Error loading data:", error);
        }
    }

    _processData(data) {
        let account_list = [];
        let account_totals = {};
        let totals = {
            deferred: 0,
            current: 0,
            not_started: 0,
            before: 0,
            later: 0
        };
        let currency = null;

        for (const [index, value] of Object.entries(data)) {
            if (index !== 'account_totals' && index !== 'journal_ids' && index !== 'analytic_ids') {
                account_list.push(index);
            } else if (index === 'journal_ids') {
                this.state.journals = value;
            } else if (index === 'analytic_ids') {
                this.state.analytics = value;
            } else if (index === 'account_totals') {
                account_totals = value;
                Object.values(account_totals).forEach(account_info => {
                    currency = account_info.currency_id;
                    totals.deferred += account_info.total || 0;
                    totals.current += account_info.current || 0;
                    totals.not_started += account_info.not_started || 0;
                    totals.before += account_info.before || 0;
                    totals.later += account_info.later || 0;
                });
            }
        }

        this.state.account = account_list;
        this.state.account_data = data;
        this.state.account_total = account_totals;
        this.state.currency = currency;
        this.state.total_deferred = totals.deferred.toFixed(2);
        this.state.total_current = totals.current.toFixed(2);
        this.state.total_not_started = totals.not_started.toFixed(2);
        this.state.total_before = totals.before.toFixed(2);
        this.state.total_later = totals.later.toFixed(2);
    }

    // Open Journal Items for specific account
    openJournalItems(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        const accountId = parseInt(ev.currentTarget.dataset.accountId);

        return this.action.doAction({
            type: "ir.actions.act_window",
            name: "Journal Items",
            res_model: 'account.move.line',
            views: [[false, "list"], [false, "form"]],
            domain: [
                ['account_id', '=', accountId],
                ['deferred_start_date', '!=', false],
                ['deferred_end_date', '!=', false],
                ['parent_state', '=', 'posted'],
                ['move_id.move_type', 'in', ['in_invoice', 'in_refund']],
                ['account_id.account_type', 'in', ['expense', 'expense_depreciation', 'expense_direct_cost']]
            ],
            context: {
                'search_default_group_by_move': true,
                'expand': true,
            },
            target: "current",
        });
    }

    // Open Annotate function
    openAnnotate(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        console.log("Annotate clicked for account:", ev.currentTarget.dataset.accountId);
    }

    async applyFilter(ev) {
        ev.preventDefault();

        try {
            const target = ev.currentTarget;
            const filterValue = target.dataset.value;
            const filterId = target.dataset.id;

            // Handle different filter types
            if (target.name === 'start_date' || target.name === 'end_date') {
                this._handleDateFilter(target);
            } else if (filterValue && ['month', 'year', 'quarter', 'last-month', 'last-year', 'last-quarter'].includes(filterValue)) {
                this.state.date_range = filterValue;
            } else if (filterValue === 'journal' && filterId) {
                this._handleJournalFilter(target, parseInt(filterId));
            } else if (filterValue === 'analytic' && filterId) {
                this._handleAnalyticFilter(target, parseInt(filterId));
            } else if (filterValue === 'draft') {
                this._handleDraftFilter(target);
            }

            // Apply filters
            await this._applyFilters();

        } catch (error) {
            console.error("Error applying filter:", error);
        }
    }

    _handleDateFilter(target) {
        if (target.name === 'start_date') {
            this.state.date_range = {
                ...this.state.date_range,
                start_date: target.value
            };
        } else if (target.name === 'end_date') {
            this.state.date_range = {
                ...this.state.date_range,
                end_date: target.value
            };
        }
    }

    _handleJournalFilter(target, journalId) {
        const checkbox = target.querySelector('.journal-checkbox');
        if (!this.state.selected_journal_list.includes(journalId)) {
            this.state.selected_journal_list.push(journalId);
            target.classList.add('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-square-o', 'fa-check-square-o');
        } else {
            this.state.selected_journal_list = this.state.selected_journal_list.filter(id => id !== journalId);
            target.classList.remove('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-check-square-o', 'fa-square-o');
        }
    }

    _handleAnalyticFilter(target, analyticId) {
        const checkbox = target.querySelector('.analytic-checkbox');
        if (!this.state.selected_analytic_list.includes(analyticId)) {
            this.state.selected_analytic_list.push(analyticId);
            target.classList.add('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-square-o', 'fa-check-square-o');
        } else {
            this.state.selected_analytic_list = this.state.selected_analytic_list.filter(id => id !== analyticId);
            target.classList.remove('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-check-square-o', 'fa-square-o');
        }
    }

    _handleDraftFilter(target) {
        const checkbox = target.querySelector('.draft-checkbox');
        if (target.classList.contains('selected-filter')) {
            const { draft, ...updatedOptions } = this.state.options || {};
            this.state.options = updatedOptions;
            target.classList.remove('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-check-square-o', 'fa-square-o');
        } else {
            this.state.options = {
                ...this.state.options,
                'draft': true
            };
            target.classList.add('selected-filter');
            if (checkbox) checkbox.className = checkbox.className.replace('fa-square-o', 'fa-check-square-o');
        }
    }

    async _applyFilters() {
        const filtered_data = await this.orm.call("deferred.report", "get_filter_values",
            [this.state.selected_journal_list, this.state.date_range, this.state.options,
             this.state.selected_analytic_list, this.state.method, 'expense']);

        this._processData(filtered_data);
        this.state.filter_applied = true;
        this.state.expandedAccounts.clear();
    }

    async printPdf(ev) {
        ev.preventDefault();
        const totals = {
            'total_deferred': this.state.total_deferred || 0,
            'total_current': this.state.total_current || 0,
            'total_not_started': this.state.total_not_started || 0,
            'total_before': this.state.total_before || 0,
            'total_later': this.state.total_later || 0,
            'currency': this.state.currency || '',
        };

        const reportData = {
            'account': this.state.account || [],
            'account_data': this.state.account_data || {},
            'total': this.state.account_total || {},
            'title': this.state.title || 'Deferred Expense Report',
            'filters': this._getFilterData(),
            'grand_total': totals,
            'report_name': this.props.action.display_name
        };

        return this.action.doAction({
            'type': 'ir.actions.report',
            'report_type': 'qweb-pdf',
            'report_name': 'dynamic_accounts_report.deferred_expense_report',
            'report_file': 'dynamic_accounts_report.deferred_expense_report',
            'data': reportData,
            'context': reportData,
            'display_name': this.props.action.display_name,
        });
    }

    async print_xlsx() {
        try {
            // التأكد من وجود البيانات
            if (!this.state.account || this.state.account.length === 0) {
                alert('No data available to export. Please ensure you have deferred expense entries.');
                return;
            }

            const totals = {
                'total_deferred': parseFloat(this.state.total_deferred) || 0,
                'total_current': parseFloat(this.state.total_current) || 0,
                'total_not_started': parseFloat(this.state.total_not_started) || 0,
                'total_before': parseFloat(this.state.total_before) || 0,
                'total_later': parseFloat(this.state.total_later) || 0,
                'currency': this.state.currency || '',
            };

            const reportData = {
                'account': this.state.account,
                'account_data': this.state.account_data,
                'total': this.state.account_total,
                'title': this.state.title || 'Deferred Expense Report',
                'filters': this._getFilterData(),
                'grand_total': totals,
            };

            const action = {
                'model': 'deferred.report',
                'data': JSON.stringify(reportData),
                'output_format': 'xlsx',
                'report_name': this.state.title || 'Deferred Expense Report',
                'report_action': this.props.action.xml_id || 'action_deferred_expense_report'
            };

            await download({
                url: '/xlsx_report',
                data: action,
                complete: () => {
                    console.log('XLSX download completed successfully');
                },
                error: (error) => {
                    console.error('XLSX export error:', error);
                    alert('Error generating Excel file. Please check console for details.');
                },
            });

        } catch (error) {
            console.error('Error in print_xlsx:', error);
            alert('Error preparing Excel export: ' + error.message);
        }
    }

    _getFilterData() {
        const selectedJournalNames = this.state.selected_journal_list.map(journalId => {
            const journal = this.state.journals.find(j => j.id === journalId);
            return journal ? journal.name : '';
        }).filter(name => name);

        const selectedAnalyticNames = this.state.selected_analytic_list.map(analyticId => {
            const analytic = this.state.analytics.find(a => a.id === analyticId);
            return analytic ? analytic.name : '';
        }).filter(name => name);

        let filters = {
            'journal': selectedJournalNames,
            'analytic': selectedAnalyticNames,
            'options': this.state.options,
            'start_date': null,
            'end_date': null,
        };

        if (this.state.date_range && typeof this.state.date_range === 'object') {
            filters['start_date'] = this.state.date_range.start_date;
            filters['end_date'] = this.state.date_range.end_date;
        }

        return filters;
    }
}

DeferredExpenseReport.defaultProps = {
    resIds: [],
};
DeferredExpenseReport.template = 'deferred_expense_template';
actionRegistry.add("deferred_expense_report", DeferredExpenseReport);