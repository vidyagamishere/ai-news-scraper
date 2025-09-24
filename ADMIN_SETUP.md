# AI News Admin Interface Setup

This admin interface provides comprehensive database management for the AI News platform with PostgreSQL integration.

## Features

✅ **Secure Authentication**
- Login with admin@vidyagam.com
- Email OTP verification system
- Session-based security

✅ **Database Management**
- View all database tables with pagination
- Full CRUD operations (Create, Read, Update, Delete)
- Real-time record counts and statistics

✅ **Data Operations**
- Download any table as CSV
- Bulk upload data via CSV files
- Add/edit individual records

✅ **System Management**
- Trigger RSS scraping manually
- Update news sources
- View system health status
- Admin role management

## Quick Start

### 1. Install Dependencies
```bash
cd ai-news-scraper/
pip install -r admin_requirements.txt
```

### 2. Set Environment Variables (Optional)
```bash
# PostgreSQL connection (default provided)
export POSTGRES_URL="postgresql://postgres:FgvftzrGueiGipLiRRMKMElppasuzBjptZlwPL@autorack.proxy.rlwy.net:51308/railway"

# Email service for OTP (optional - will use debug mode if not set)
export BREVO_API_KEY="your_brevo_api_key"

# Secret key for sessions (default provided)
export SECRET_KEY="ai-news-admin-secret-key-2025"
```

### 3. Run Admin Interface
```bash
python run_admin.py
```

### 4. Access Admin Panel
- Open browser: `http://localhost:5001`
- Login email: `admin@vidyagam.com`
- Enter OTP sent to email (or use debug OTP if email service not configured)

## Usage Guide

### Login Process
1. Enter admin email (pre-filled: admin@vidyagam.com)
2. Click "Send OTP"
3. Check email for OTP code (or debug display if email service not configured)
4. Enter 6-digit OTP code
5. Access admin dashboard

### Dashboard Features

**Table Management Cards**
- View record counts for each table
- Quick access to manage any table
- Download table data as CSV
- Upload new data via CSV

**Quick Actions**
- **Trigger Scraping**: Manually start RSS news scraping
- **Update RSS Sources**: Refresh news source configurations  
- **System Health**: Check backend API status
- **Export All Data**: Download complete database export

### Table Operations

**View Table Data**
- Paginated table view with search and sorting
- Record details with proper data type formatting
- Bulk select and delete operations

**Add Records**
- Dynamic form generation based on table structure
- Required field validation
- Data type enforcement

**Edit Records**  
- In-place editing with modal forms
- Validation for data integrity
- Real-time updates

**Delete Operations**
- Single record deletion with confirmation
- Bulk delete for multiple records
- Safe deletion with referential integrity checks

**CSV Operations**
- **Download**: Export any table to CSV format
- **Upload**: Bulk import data from CSV files
- Column mapping and validation
- Error reporting for failed imports

## File Structure

```
ai-news-scraper/
├── admin_interface.py          # Main Flask application
├── admin_requirements.txt      # Python dependencies
├── run_admin.py               # Application runner with setup
├── templates/
│   ├── base.html              # Base template with navigation
│   ├── admin_login.html       # OTP authentication interface
│   ├── admin_dashboard.html   # Main dashboard
│   └── table_view.html        # Table data management
└── ADMIN_SETUP.md            # This setup guide
```

## Database Integration

The admin interface connects to your PostgreSQL database on Railway:
- **Automatic Role Column**: Adds 'role' column to users table if missing
- **Admin Identification**: Sets admin@vidyagam.com as admin user
- **Safe Operations**: All database operations include error handling and validation

## Security Features

- **Email OTP Authentication**: Secure login with time-limited OTP codes
- **Session Management**: Flask sessions with secure cookie handling  
- **Admin Role Validation**: Role-based access control
- **CSRF Protection**: Form validation and secure data handling
- **Input Sanitization**: SQL injection protection with parameterized queries

## Troubleshooting

### Database Connection Issues
```bash
# Test connection manually
python -c "import psycopg2; conn = psycopg2.connect('your_postgres_url'); print('✅ Connected')"
```

### Email Service Issues
- If BREVO_API_KEY not set, OTP will display in debug mode
- Check browser console for OTP code if email delivery fails
- Verify admin email is correct in login form

### Port Conflicts
- Default port: 5001
- Change in `run_admin.py` if needed: `app.run(port=5002)`

### Permission Issues
- Ensure PostgreSQL user has full table permissions
- Check Railway database access settings

## API Integration

The admin interface integrates with your existing AI News backend:
- **Scraping Trigger**: `POST /scrape` - Start manual RSS scraping
- **Source Updates**: `POST /admin/update-sources` - Refresh news sources
- **Health Check**: `GET /health` - System status monitoring

## Development

To extend the admin interface:

1. **Add New Tables**: Tables are automatically detected from database schema
2. **Custom Validations**: Edit `validate_record_data()` in `admin_interface.py`
3. **New Features**: Add routes to Flask app and corresponding templates
4. **Styling**: Modify Bootstrap classes in templates for custom appearance

## Production Deployment

For production deployment:
1. Set proper environment variables
2. Use production WSGI server (gunicorn, uwsgi)
3. Configure reverse proxy (nginx)
4. Enable HTTPS for secure sessions
5. Set up proper email service for OTP delivery

```bash
# Production example
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 admin_interface:app
```

## Support

The admin interface is designed to be intuitive and self-explanatory. All operations include confirmation dialogs and error handling for safe database management.

For issues or feature requests, check the application logs or browser developer console for detailed error information.