# -*- coding: utf-8 -*-
{
    "name" : "School Management",
    "version" : "0.1",
    "category" : "Accounting",
    "sequence": 60,
    "complexity" : "normal",
    "author" : "ColourCog.com",
    "website" : "http://colourcog.com",
    "depends" : [
        "base",
        "sale",
        "account",
    ],
    "summary" : "Adds School Management functionalities",
    "description" : """
School Management
========================
This module offers tools to manage primary and secondary schools

Features:
-------------------------------
* Student database
* Registration process
    """,
    "data" : [
      "security/ir.model.access.csv",
      'top_menu.xml',
      'student_view.xml',
      'res_config_view.xml',
    ],
    "application": False,
    "installable": True
}

