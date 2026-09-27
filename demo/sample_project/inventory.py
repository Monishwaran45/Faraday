def get_last_n_items(items, n):
    """Return the last n items from the list."""
    # BUG: off-by-one — this drops the final element instead of including it
    return items[len(items) - n - 1:len(items) - 1]


def apply_discount(price, percent):
    """Apply a percentage discount to a price."""
    # BUG: no validation — negative or >100 percent silently produces
    # nonsensical results (e.g. negative price)
    return price - (price * percent / 100)


def divide_stock(total_stock, num_warehouses):
    # BUG: no check for num_warehouses == 0 -> ZeroDivisionError at runtime
    return total_stock / num_warehouses
