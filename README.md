# EasyPharma Wholesale - MVP

A complete, responsive Pharma Wholesale Management System built with Django, HTML, CSS, and JavaScript.

## Features

### Dashboard
- Key metrics (Total Products, Customers, Orders, Revenue)
- Order status overview
- Recent orders tracking
- Low stock alerts
- Visual statistics cards

### Product Management
- List all products with search and category filter
- Create, edit, and delete products
- Track inventory levels
- Batch and expiry date management
- Profit margin calculation
- Stock level alerts

### Customer Management
- Manage pharmacy customers
- Track customer contact information
- View customer order history
- Search and filter customers

### Order Management
- Create orders with dynamic item addition
- Track order status (Pending, Completed, Cancelled)
- View detailed order information
- Update order status
- Calculate order totals automatically

### Categories
- Manage product categories
- Organize products by category

### Reports & Analytics
- Monthly sales tracking
- Sales by category analysis
- Top 10 selling products
- Revenue insights

## Technology Stack

- **Backend**: Django 6.0.6
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite3
- **Icons**: Font Awesome 6.4.0
- **Design**: Responsive, Mobile-First

## Installation

### Prerequisites
- Python 3.11+
- pip
- Git

### Setup

1. Clone the repository:
```bash
git clone https://github.com/farooq1993/easy-pharma-wholesale.git
cd easy-pharma-wholesale
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run migrations:
```bash
python3 manage.py migrate
```

5. Create a superuser:
```bash
python3 manage.py createsuperuser
```

6. Run the development server:
```bash
python3 manage.py runserver
```

7. Access the application:
- Main app: http://localhost:8000/
- Admin panel: http://localhost:8000/admin/

## Deploy on Vercel

This project is configured as a Vercel Python function. Vercel's filesystem is
temporary, so production must use a hosted PostgreSQL database such as Neon;
do not rely on `db.sqlite3` for deployed data.

1. Create a PostgreSQL database on Neon (or another hosted PostgreSQL provider)
	and copy its connection string.
2. Push this repository to GitHub and import it into Vercel. Keep the project
	root at the folder containing `manage.py` and `vercel.json`.
3. In Vercel Project Settings -> Environment Variables, add these variables for
	Production (and Preview if needed):

	- `DJANGO_SECRET_KEY`: a long random secret
	- `DJANGO_DEBUG`: `False`
	- `DATABASE_URL`: the PostgreSQL connection string, including SSL if your
	  provider requires it
	- `ALLOWED_HOSTS`: `.vercel.app` plus your custom domain, comma-separated
	- `CSRF_TRUSTED_ORIGINS`: `https://your-project.vercel.app` plus your custom
	  HTTPS domain, comma-separated

4. Deploy. Vercel runs `python manage.py collectstatic --noinput` from
	`vercel.json`, and WhiteNoise serves the collected assets.
5. Run migrations against the hosted database from the repository root:

	```bash
	python manage.py migrate
	python manage.py createsuperuser
	```

	Set `DATABASE_URL` in the shell before running these commands. Alternatively,
	run the same commands from a one-off deployment environment with the Vercel
	production variables loaded.

The local `.env` file is ignored by Git. Use `.env.example` as the variable
template and never commit database credentials or secret keys.

## Project Structure

```
easy-pharma-wholesale/
├── easyPharma_wholesale/      # Main project settings
│   ├── settings.py            # Django settings
│   ├── urls.py                # Main URL configuration
│   └── wsgi.py
├── wholesaleApp/              # Main application
│   ├── models.py              # Database models
│   ├── views.py               # View functions
│   ├── admin.py               # Admin configuration
│   ├── urls/                  # URL routing
│   └── migrations/            # Database migrations
├── templates/                 # HTML templates
│   ├── base.html              # Base template
│   ├── dashboard.html
│   ├── products/
│   ├── customers/
│   ├── orders/
│   ├── categories/
│   └── reports.html
├── static/                    # Static files
│   ├── css/
│   └── js/
├── manage.py
└── requirements.txt
```

## Database Models

### Category
- name (CharField)
- description (TextField)

### Product
- name (CharField)
- sku (CharField, unique)
- category (ForeignKey)
- manufacturer (CharField)
- batch_number (CharField)
- expiry_date (DateField)
- purchase_price (DecimalField)
- sale_price (DecimalField)
- stock_quantity (IntegerField)
- min_stock_level (IntegerField)

### Customer
- name (CharField)
- pharmacy_name (CharField)
- phone (CharField)
- email (EmailField)
- address (TextField)

### Order
- customer (ForeignKey)
- order_date (DateTimeField)
- total_amount (DecimalField)
- status (CharField: Pending, Completed, Cancelled)

### OrderItem
- order (ForeignKey)
- product (ForeignKey)
- quantity (IntegerField)
- unit_price (DecimalField)
- subtotal (DecimalField)

## URL Routes

### Dashboard
- `/` - Dashboard home

### Products
- `/products/` - List products
- `/products/create/` - Create product
- `/products/<id>/` - View product
- `/products/<id>/edit/` - Edit product
- `/products/<id>/delete/` - Delete product

### Customers
- `/customers/` - List customers
- `/customers/create/` - Create customer
- `/customers/<id>/` - View customer
- `/customers/<id>/edit/` - Edit customer
- `/customers/<id>/delete/` - Delete customer

### Orders
- `/orders/` - List orders
- `/orders/create/` - Create order
- `/orders/<id>/` - View order
- `/orders/<id>/status/` - Update order status

### Categories
- `/categories/` - List categories
- `/categories/create/` - Create category

### Reports
- `/reports/` - View reports and analytics

### Admin
- `/admin/` - Django admin panel

## API Endpoints

- `/api/products/` - Get all products as JSON
- `/api/customers/` - Get all customers as JSON

## Features Highlights

✅ **Fully Responsive Design** - Works on mobile, tablet, and desktop
✅ **Modern UI** - Gradient colors, smooth transitions, professional design
✅ **Search & Filter** - Find products and customers quickly
✅ **Real-time Calculations** - Automatic total calculations in orders
✅ **Status Tracking** - Color-coded status badges
✅ **Stock Management** - Low stock alerts
✅ **Admin Panel** - Full Django admin interface
✅ **Data Analytics** - Sales reports and insights
✅ **User-Friendly** - Intuitive navigation and forms

## Future Enhancements

- [ ] User authentication and roles
- [ ] Invoice generation (PDF)
- [ ] Email notifications
- [ ] Payment integration
- [ ] Advanced reporting with charts
- [ ] Bulk import/export
- [ ] Mobile app
- [ ] API documentation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Support

For support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for EasyPharma Wholesale**
