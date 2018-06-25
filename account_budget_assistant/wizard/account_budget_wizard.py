# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import ValidationError

class AccountBudgetWizard(models.TransientModel):
    _name = 'account.budget.wizard'

    @api.model
    def _get_from(self):
        ctx = self._context
        return 'active_id' in ctx and self.env['crossovered.budget'].browse(ctx['active_id']).date_from or False
        
    @api.model
    def _get_to(self):
        ctx = self._context
        return 'active_id' in ctx and self.env['crossovered.budget'].browse(ctx['active_id']).date_to or False
    
    date_from = fields.Date('Inicio', required=True, default=_get_from)
    date_to = fields.Date('Fin', required=True, default=_get_to)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Cuenta analítica')
    amount = fields.Float('Monto por defecto', help="Monto planificado por defecto a aplicar a todas las líneas")
    general_budget_id = fields.Many2one('account.budget.post', 'Posición Presupuestaria', required=True)
    frequence = fields.Selection([
        ('12', 'Anual'),
        ('6', 'Semestral'),
        ('3', 'Trimestral'),
        ('2', 'Bimensual'),
        ('1', 'Mensual'),
        ],'Frecuencia', required=True, default='1')
    line_ids = fields.One2many('account.budget.wizard.line','wizard_id', 'Líneas')

    @api.onchange('amount')
    def onchange_amount(self):
        if self.amount != 0.0:
            self.line_ids.update({'planned_amount': self.amount})
    
    @api.onchange('frequence')
    def onchange_frequence(self):
        fmt = '%Y-%m-%d'
        line_qty = 12/int(self.frequence)
        lines = []
        date_for = datetime.strptime(self.date_from,fmt)
        for i in range(line_qty):
            date_line = date_for + relativedelta(months=int(self.frequence))
            lines.append((0,0,{
                'date_from': date_for,
                'date_to': date_line - timedelta(days=1),
            }))
            date_for = date_line
        self.line_ids = lines

    @api.one
    def make_budget_lines(self):
        budget = self.env['crossovered.budget'].browse(self._context['active_id'])
        if budget.state != 'draft':
            raise ValidationError('El presupuesto no está en Borrador, no es posible agregar lineas')
        for line in self.line_ids:
            self.env['crossovered.budget.lines'].create({
                'general_budget_id': self.general_budget_id.id,
                'crossovered_budget_id': budget.id,
                'analytic_account_id': self.analytic_account_id and self.analytic_account_id.id or False,
                'date_from': line.date_from,
                'date_to': line.date_to,
                'planned_amount': line.planned_amount
            })

class AccountBudgetWizardLine(models.TransientModel):
    _name = 'account.budget.wizard.line'

    date_from = fields.Date('Inicio', required=True)
    date_to = fields.Date('Fin', required=True)
    planned_amount = fields.Float('Monto Planificado', digits=0)
    wizard_id = fields.Many2one('account.budget.wizard', 'Wizard Padre')
