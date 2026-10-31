"""
billing/management/commands/run_billing.py
=========================================
Purpose:
    Management command to automate recurring billing across all active subscribers.
    Scans for subscriptions with next_invoice_date <= today and calls generate_invoice().

Usage:
    python manage.py run_billing
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from subscriptions.models import Subscription
from billing.services import generate_invoice


class Command(BaseCommand):
    help = "Generates recurring invoices for active subscriptions whose next_invoice_date <= today."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulates billing without persisting any invoices to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        today = timezone.localdate()

        self.stdout.write(self.style.NOTICE(f"Starting billing run for date: {today}"))

        # Find active subscriptions that are due for renewal / billing
        due_subscriptions = (
            Subscription.objects.filter(
                status=Subscription.STATUS_ACTIVE,
                next_invoice_date__lte=today,
            )
            .select_related("customer", "plan")
            .prefetch_related("lines__product")
        )

        total_due = due_subscriptions.count()
        self.stdout.write(f"Found {total_due} active subscription(s) due for billing.")

        processed = 0
        for sub in due_subscriptions:
            self.stdout.write(f" -> Processing {sub.number} for customer {sub.customer.email}...")

            if not dry_run:
                # Calls the atomic billing service stub
                invoice = generate_invoice(sub)
                if invoice:
                    self.stdout.write(self.style.SUCCESS(f"    Created invoice: {invoice.number}"))
                else:
                    self.stdout.write(self.style.WARNING("    [STUB] generate_invoice returned None (Service is a stub)."))
            else:
                self.stdout.write(self.style.NOTICE("    [DRY-RUN] Skipped persistence."))

            processed += 1

        self.stdout.write(self.style.SUCCESS(f"Billing run completed. {processed} subscription(s) evaluated."))
