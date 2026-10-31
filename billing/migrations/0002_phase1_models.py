# Generated for Phase 1 Billing Models

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def migrate_existing_data(apps, schema_editor):
    Invoice = apps.get_model("billing", "Invoice")
    Payment = apps.get_model("billing", "Payment")

    status_map = {
        "Draft": "DRAFT",
        "Confirmed": "CONFIRMED",
        "Paid": "PAID",
        "Cancelled": "DRAFT",
    }
    for inv in Invoice.objects.order_by().all():
        if inv.status in status_map:
            inv.status = status_map[inv.status]
            inv.save(update_fields=["status"])

    method_map = {
        "credit_card": "CARD",
        "bank_transfer": "BANK_TRANSFER",
        "upi": "UPI",
        "cash": "CASH",
        "stripe": "OTHER",
    }
    for pmt in Payment.objects.order_by().all():
        if pmt.method in method_map:
            pmt.method = method_map[pmt.method]
            pmt.save(update_fields=["method"])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('billing', '0001_initial'),
    ]

    operations = [
        # 1. Create Discount model
        migrations.CreateModel(
            name='Discount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Display title of the discount (e.g. VIP Partner Discount).', max_length=150)),
                ('code', models.CharField(help_text='Unique redemption code (e.g. SAVE20).', max_length=50, unique=True)),
                ('type', models.CharField(choices=[('FIXED', 'Fixed Amount'), ('PERCENTAGE', 'Percentage')], default='FIXED', help_text='Type of deduction: FIXED currency amount or PERCENTAGE rate.', max_length=20)),
                ('value', models.DecimalField(decimal_places=2, help_text='Discount amount in currency or percentage value (0-100).', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('valid_from', models.DateField(blank=True, help_text='Start date of discount validity window.', null=True)),
                ('valid_to', models.DateField(blank=True, help_text='End date of discount validity window.', null=True)),
                ('usage_limit', models.PositiveIntegerField(blank=True, help_text='Maximum number of times this discount can be redeemed overall (None for unlimited).', null=True)),
                ('times_used', models.PositiveIntegerField(default=0, help_text='Current count of successful redemptions.')),
                ('is_active', models.BooleanField(default=True, help_text='Toggles whether this discount is currently eligible for application.')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Discount',
                'verbose_name_plural': 'Discounts',
                'ordering': ['-created_at'],
            },
        ),

        # 2. Rename Invoice fields
        migrations.RenameField(
            model_name='invoice',
            old_name='number',
            new_name='invoice_number',
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='discount_amount',
            new_name='discount_total',
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='tax_amount',
            new_name='tax_total',
        ),

        # 3. Add new fields to Invoice
        migrations.AddField(
            model_name='invoice',
            name='issue_date',
            field=models.DateField(default=django.utils.timezone.localdate, help_text='Date this invoice was officially issued.'),
        ),
        migrations.AddField(
            model_name='invoice',
            name='discount',
            field=models.ForeignKey(blank=True, help_text='Optional discount coupon applied to this invoice.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoices', to='billing.discount'),
        ),

        # 4. Update fields on Invoice
        migrations.AlterField(
            model_name='invoice',
            name='invoice_number',
            field=models.CharField(editable=False, help_text='Unique auto-generated invoice reference number (e.g. INV-202610-0012).', max_length=32, unique=True),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='discount_total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total discount deducted from the subtotal.', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='subtotal',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Gross total of all invoice line items before discounts and taxes.', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='tax_total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Total sales tax applied across all line items.', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='total',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Final payable balance (subtotal - discount_total + tax_total).', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))]),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='status',
            field=models.CharField(choices=[('DRAFT', 'Draft'), ('CONFIRMED', 'Confirmed'), ('PAID', 'Paid')], db_index=True, default='DRAFT', max_length=20),
        ),

        # 5. Update constraints on Invoice
        migrations.RemoveConstraint(
            model_name='invoice',
            name='unique_subscription_period_billing',
        ),
        migrations.AddConstraint(
            model_name='invoice',
            constraint=models.UniqueConstraint(fields=('subscription', 'period_start'), name='unique_invoice_per_subscription_period'),
        ),

        # 6. Rename Payment fields
        migrations.RenameField(
            model_name='payment',
            old_name='date',
            new_name='payment_date',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='note',
            new_name='reference',
        ),

        # 7. Alter Payment options (ordering by -payment_date, -created_at)
        migrations.AlterModelOptions(
            name='payment',
            options={'ordering': ['-payment_date', '-created_at'], 'verbose_name': 'Payment', 'verbose_name_plural': 'Payments'},
        ),

        # 8. Add recorded_by to Payment
        migrations.AddField(
            model_name='payment',
            name='recorded_by',
            field=models.ForeignKey(blank=True, help_text='Staff member or user who logged this payment transaction.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_payments', to=settings.AUTH_USER_MODEL),
        ),

        # 9. Alter Payment fields
        migrations.AlterField(
            model_name='payment',
            name='amount',
            field=models.DecimalField(decimal_places=2, help_text='Payment amount in currency.', max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))]),
        ),
        migrations.AlterField(
            model_name='payment',
            name='payment_date',
            field=models.DateField(default=django.utils.timezone.localdate, help_text='Date this payment was executed.'),
        ),
        migrations.AlterField(
            model_name='payment',
            name='method',
            field=models.CharField(choices=[('CASH', 'Cash'), ('CARD', 'Card'), ('BANK_TRANSFER', 'Bank Transfer'), ('UPI', 'UPI'), ('OTHER', 'Other')], default='CARD', max_length=30),
        ),
        migrations.AlterField(
            model_name='payment',
            name='reference',
            field=models.CharField(blank=True, default='', help_text='Transaction reference number or gateway identifier.', max_length=255),
        ),

        # 10. Alter InvoiceLine fields
        migrations.AlterField(
            model_name='invoiceline',
            name='unit_price',
            field=models.DecimalField(decimal_places=2, max_digits=12),
        ),
        migrations.AlterField(
            model_name='invoiceline',
            name='amount',
            field=models.DecimalField(decimal_places=2, default=Decimal('0.00'), help_text='Line subtotal before tax.', max_digits=12),
        ),

        # 11. Data migration to normalize status and method
        migrations.RunPython(migrate_existing_data, reverse_code=migrations.RunPython.noop),
    ]
