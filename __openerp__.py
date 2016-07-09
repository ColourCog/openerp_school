# -*- coding: utf-8 -*-
{
    "name" : "School Management",
    "version" : "0.11",
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
* registration process
* enrolment process
* Automatic invoice generation
* Subjects and grading
    """,
    "data" : [
      "security/ir_rule.xml",
      "security/ir.model.access.csv",
      'top_menu.xml',
      'general_view.xml',
      'sclass_view.xml',
      'academic_period_view.xml',
      'academic_year_view.xml',
      'student_view.xml',
      'student_workflow.xml',
      'student_sequence.xml',
      'student_data.xml',
      'health_view.xml',
      'enrolment_view.xml',
      'enrolment_workflow.xml',
      'enrolment_data.xml',
      'grading_view.xml',
      'res_config_view.xml',
      'wizards_registration_import_invoice_view.xml',
      'wizards_enrolment_import_invoice_view.xml',
      'wizards_academic_period_new_view.xml',
      'wizards_enrolment_promote_view.xml',
      'wizards_class_promote_view.xml',
      'school_report.xml',
      'school_data.xml',
    ],
    "application": False,
    "installable": True
}

