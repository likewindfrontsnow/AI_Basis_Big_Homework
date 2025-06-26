# utils.py
import time
import functools

def retry(max_retries=3, delay=2, allowed_exceptions=()):
    """
    A decorator to retry a function if it raises an exception.

    :param max_retries: Maximum number of retries.
    :param delay: Delay between retries in seconds.
    :param allowed_exceptions: A tuple of exceptions that should trigger a retry. 
                               If empty, retries on any Exception.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    # If specific exceptions are listed, only retry for them.
                    if allowed_exceptions and not isinstance(e, allowed_exceptions):
                        raise # Re-raise exception if it's not in the allowed list

                    attempts += 1
                    if attempts >= max_retries:
                        print(f"Function '{func.__name__}' failed after {max_retries} attempts. Re-raising last exception.")
                        raise e
                    
                    print(f"Attempt {attempts}/{max_retries} for '{func.__name__}' failed with error: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator