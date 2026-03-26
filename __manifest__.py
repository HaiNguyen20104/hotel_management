# -*- coding: utf-8 -*-
{
    'name': 'Hotel Management',
    'version': '18.0.1.0.0',
    'category': 'Services/Hotel',
    'summary': 'Comprehensive Hotel Management System',
    'description': """
        Hotel Management System
        =======================
        * Quản lý phòng (F1)
        * Quản lý loại phòng (F2)
        * Tra cứu phòng trống (F3)
        * Đặt phòng (F4)
        * Quản lý khách hàng (F5)
        * Quản lý nhân viên (F6)
        * Quản lý hóa đơn thuê (F7)
        * Theo dõi trạng thái phòng (F8)
        * Thống kê báo cáo (F9)
    """,
    'author': 'Your Name',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'web',
    ],
    'data': [
        # Security
        'security/security_groups.xml',
        'security/ir.model.access.csv',

        # Data
        'data/ir_sequence_data.xml',
        'data/room_type_data.xml',

        # Views
        'views/room_type_views.xml',
        'views/room_views.xml',
        'views/user_views.xml',
        'views/reservation_views.xml',
        'views/rental_views.xml',
        'views/invoice_views.xml',
        'views/menu_views.xml',

        # Wizards
        'wizards/checkin_wizard_views.xml',
        'wizards/checkout_wizard_views.xml',
        'wizards/change_room_wizard_views.xml',

        # Reports
        'reports/invoice_report.xml',

        # Demo data (optional)
        # 'data/demo_data.xml',
    ],
    'demo': [
        # 'data/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hotel_management/static/src/**/*',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
