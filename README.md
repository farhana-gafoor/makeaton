# BrightLoop - Subscription Management System

> **8-Hour Hackathon Starter Skeleton**  
> Built with Python 3, Django, SQLite, server-rendered Django templates, and local Bootstrap 5 (100% offline, zero CDN dependencies).

---

## 🌟 Overview & Architecture

BrightLoop is a modular subscription management and recurring billing engine. The project is split into **5 independent apps** so a team of 4 developers can work in parallel with minimal Git merge conflicts:

| Developer | App Area | Primary Responsibilities |
|---|---|---|
| **Dev 1** | `accounts/` | Custom User model, email login, roles (Admin/Staff/Customer), password reset flow, query isolation helper |
| **Dev 2** | `catalog/` | Products, variants, subscription plans, taxes, discounts, and model validation |
| **Dev 3** | `subscriptions/` | Quotations, subscription contracts, line items, status state-machine transitions |
| **Dev 4** | `billing/` & `dashboard/` | Invoices, payments, automated billing runner stub, and executive finance analytics |

---

## 🚀 Quickstart: Setup & Run (Step-by-Step)

### 1. Prerequisites
- Python 3.10+ (Tested with Python 3.14)
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/shifnn-tech/makeaton.git
cd makeaton
```

### 3. Create and Activate Virtual Environment
- **On Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```
- **On macOS / Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Apply Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Seed Demo Data
Populate the database with sample products, plans, taxes, discounts, 1 Admin, 2 Staff, and 20 Customer accounts:
```bash
python manage.py seed_data
```

*(Optional)* To test heavy database performance with **3,000+ subscriptions and 10,000+ invoices** via `bulk_create`:
```bash
python manage.py seed_data --big
```

### 7. Run the Development Server
```bash
python manage.py runserver
```
Visit **http://127.0.0.1:8000/** in your browser.

---

## 🔑 Default Seed Credentials

All seed accounts use the password: `SecurePassword@123`

| Role | Email | Password | Access Privileges |
|---|---|---|---|
| **Admin** | `admin@brightloop.local` | `SecurePassword@123` | Full access, Django Admin, Create Staff, Finance Dashboard |
| **Staff** | `staff1@brightloop.local` | `SecurePassword@123` | Manage Subscriptions, Invoices, Finance Dashboard |
| **Customer** | `customer1@brightloop.local` | `SecurePassword@123` | Self-service portal (own subscriptions and invoices only) |

---

## 📂 App Breakdown & File Directory

### 1. `accounts/` (Authentication & Role Security)
- **`models.py`**: Custom `User` model (`AbstractUser`) using `email` as `USERNAME_FIELD` and a `role` field (`admin`, `staff`, `customer`).
- **`validators.py`**: `CustomComplexityValidator` requiring >8 characters, uppercase, lowercase, and special characters.
- **`decorators.py`**: `@role_required("admin", "staff")` and `RoleRequiredMixin` to enforce RBAC on views.
- **`utils.py`**: `filter_by_user(queryset, user)` ensures customers only ever see their own records.
- **`forms.py`**: `CustomerSignUpForm` (creates customers only), `LoginForm`, and `StaffCreationForm` (admin only).
- **`views.py`**: Sign up, sign in, sign out, staff creation, and role-aware landing page.
- **`urls.py`**: Authentication routes and Django's built-in password reset views.
- **`admin.py`**: Custom `UserAdmin` organized by email and roles.
- **`management/commands/seed_data.py`**: Database seeder with sample accounts and `--big` scale support.

### 2. `catalog/` (Products, Plans, Pricing Rules)
- **`models.py`**:
  - `Product`: Base sellable item (`service`, `physical`, `digital`) with sales and cost price.
  - `ProductVariant`: Variations (e.g. Attribute='Brand', Value='Odoo', Extra Price=560).
  - `Plan`: Recurring subscription plans (`daily`, `weekly`, `monthly`, `yearly`) with auto-close, closable, pausable, and renewable flags.
  - `Tax`: Percentage rate between 0.00% and 100.00%.
  - `Discount`: Fixed or percentage discounts with start/end dates, minimum purchase, usage limits, and product targeting.
  - *Model Validators*: Non-negative prices, valid date ranges, and percentage at most 100%.
- **`views.py` & `urls.py`**: Publicly browsable subscription plan and product catalogs.
- **`admin.py`**: Admin panels with inline variant editing.

### 3. `subscriptions/` (Contracts & Quotations)
- **`models.py`**:
  - `QuotationTemplate` & `TemplateLine`: Bundles to quickly quote multi-item subscriptions.
  - `Subscription`: Main recurring contract. Auto-generates unique number (`SUB-YYYYMM-XXXX`). Includes indexed fields on `status`, `customer`, and `next_invoice_date`.
  - `SubscriptionLine`: Itemized products, quantities, taxes, and amounts.
  - *State Machine*: `Draft -> Quotation -> Confirmed -> Active -> Closed` defined in a single transition dictionary. `change_status()` rejects invalid transitions.
- **`views.py` & `urls.py`**: Scoped views where customers only access their own contracts.
- **`admin.py`**: Admin setup with `SubscriptionLineInline`.

### 4. `billing/` (Invoices, Payments & Automation)
- **`models.py`**:
  - `Invoice`: Billing statement with `UniqueConstraint(fields=['subscription', 'period_start'])` to prevent double-billing.
  - `InvoiceLine`: Itemized invoice lines with tax and unit amounts.
  - `Payment`: Financial transaction records with strict validation (must be positive and cannot exceed remaining balance). Automatically transitions invoice to `Paid` once settled.
  - *Dynamic Properties*: `amount_paid` and `balance_due` calculated dynamically (never cached stale).
  - *QuerySet Helper*: `Invoice.objects.overdue()` queries `due_date < today` and `status != 'Paid'`.
- **`services.py`**: Atomic transaction stub `generate_invoice(subscription)` with detailed step-by-step instructions.
- **`management/commands/run_billing.py`**: Runner command finding active subscriptions with `next_invoice_date <= today`.
- **`admin.py`**: Invoice administration with payment and invoice line inlines.

### 5. `dashboard/` (Executive & Financial Analytics)
- **`views.py`**:
  - Computes Active Subscriptions, Total Revenue, Outstanding Amount, and Overdue Invoices.
  - Optimized with database-level `aggregate(Sum(...))`, `select_related(...)` to eliminate N+1 queries, and `Paginator` for instant page loads.
- **`templates/dashboard/finance.html`**: Financial KPI metric cards, urgent overdue watchlist, and paginated invoice table.

### 6. UI & Styling (`templates/` & `static/`)
- **`templates/base.html`**: Bootstrap 5 shell with brand CSS variables, responsive role-based navigation, user dropdown, messages display, and print styles.
- **`static/css/bootstrap.min.css` & `static/js/bootstrap.bundle.min.js`**: Local Bootstrap 5 files for 100% offline development.
- **`static/css/style.css`**: CSS custom variables (`--primary-color`), role badges, and print media rules.
- **`templates/includes/form_errors.html`**: Reusable form error display.
- **`templates/includes/pagination.html`**: Reusable pagination controls.

---

## ⚡ Background Commands & Automation

1. **Run Recurring Billing Cycle:**
   ```bash
   python manage.py run_billing
   ```
   *(Add `--dry-run` to simulate without saving changes)*

2. **Trigger Database Seeder:**
   ```bash
   python manage.py seed_data
   ```

3. **Check System Health:**
   ```bash
   python manage.py check
   ```
