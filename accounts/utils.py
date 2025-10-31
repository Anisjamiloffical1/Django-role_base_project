from datetime import date
from .models import Invoice, Order

def generate_monthly_invoice(customer):
    today = date.today()
    invoice, created = Invoice.objects.get_or_create(
        customer=customer,
        year=today.year,
        month=today.month,
    )
    invoice.calculate_total()
    return invoice
