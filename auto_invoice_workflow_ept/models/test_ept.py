from odoo import models, fields, api
class test_ept(models.Model):
    _name="test.ept"
    Char,Boolean,Integer,Float,Text,Html,Date,Datetime 
    
    name 
    is_allow_peri