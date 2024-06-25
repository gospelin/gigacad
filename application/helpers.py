from .models import Student
import random, string


def generate_unique_username(first_name, last_name):
    username = f"{first_name.strip().lower()}.{last_name.strip().lower()}"
    existing_user = Student.query.filter_by(username=username).first()
    if existing_user:
        random_suffix = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=4)
        )
        username = f"{username}{random_suffix}"
    return username


def calculate_grade(total):
    if total >= 95:
        return "A+"
    elif total >= 80:
        return "A"
    elif total >= 70:
        return "B+"
    elif total >= 65:
        return "B"
    elif total >= 60:
        return "C+"
    elif total >= 50:
        return "C"
    elif total >= 40:
        return "D"
    elif total >= 30:
        return "E"
    else:
        return "F"


def get_remark(total):
    if total >= 95:
        return "Outstanding"
    elif total >= 80:
        return "Excellent"
    elif total >= 70:
        return "Very Good"
    elif total >= 65:
        return "Good"
    elif total >= 60:
        return "Credit"
    elif total >= 50:
        return "Credit"
    elif total >= 40:
        return "Poor"
    elif total >= 30:
        return "Very Poor"
    else:
        return "Failed"


# routes.py
def calculate_grand_total(results):
    return sum(result.total for result in results)


def get_last_term(current_term):
    term_sequence = ["First Term", "Second Term", "Third Term"]
    if current_term in term_sequence:
        current_index = term_sequence.index(current_term)
        last_index = current_index - 1 if current_index > 0 else None
        return term_sequence[last_index] if last_index is not None else None
    return None


def calculate_average(results):
    total = sum(result.total for result in results)
    return total / len(results) if results else 0


def calculate_cumulative_average(results, current_term_average):
    """
    Calculate the cumulative average based on the previous term's average and the current term's average.

    Args:
        results (list): A list of result objects, each having a 'last_term_average' attribute.
        current_term_average (float): The average for the current term.

    Returns:
        float: The calculated cumulative average.
    """
    last_term_average = 0
    cumulative_average = current_term_average
    if results:
        # Assuming results is a list of objects with a 'last_term_average' attribute
        last_term_average = (
            float(results[0].last_term_average) if results[0].last_term_average else 0
        )

    if last_term_average and current_term_average:
        cumulative_average = (last_term_average + current_term_average) / 2

    return cumulative_average
