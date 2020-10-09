from odoo import api, fields, models
from odoo.exceptions import ValidationError



class ModelContEventos(models.Model):
    _inherit = 'model.cont.eventos'

    details_view = fields.Selection([
        ('type1', 'Type 1'),
        ('type2', 'Type 2'),
        ('type3', 'Type 3'),
        ('type4', 'Type 4'),
        ('type5', 'Type 5'),
    ], 'View for details', help='Define the view for details on the payment request.')
    
    encabezado_view = fields.Selection([
        ('type1', 'Type 1'),
        ('type2', 'Type 2'),
        ('type3', 'Type 3'),
        ('type4', 'Type 4'),
        ('type5', 'Type 5'),
        ('type6', 'Type 6'),
        ('type7', 'General'),
    ], 'Vista de Encabezado',help='Define la vista para el encabezado de solicitudes de pago')
    precomprometido = fields.Boolean("Precomprometido")
    solicitud_pago = fields.Boolean("Solicitud de Pago")
    recibo = fields.Boolean("Recibo")
    carta_aceptacion = fields.Boolean("Reporte Carta de Aceptacion")
    contrarecibo = fields.Boolean("Contrarecibo")
    reporte_devoluciones = fields.Boolean("Reporte Devoluciones")
    layout_beneficarios = fields.Boolean("Layout")
    informe = fields.Boolean("Campo Informes")
    fecha_vencimiento = fields.Boolean("Campo Fecha de Vencimiento")
    comprobacion_gastos = fields.Boolean("Comprobacion de Gastos")
    anios_anteriores = fields.Boolean("Filtro")
    
    @api.constrains("encabezado_view","details_view")
    def check_vista_general(self):
        if self.encabezado_view=="type7" and self.details_view not in ("type2","type4","type5"):
            raise ValidationError(
                    """Para este encabezado solo se pueden utilizar los detalles 2,4 y 5.
                                          """
                    % ()
                ) 
        