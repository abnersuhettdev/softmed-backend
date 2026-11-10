import os

import stripe
from dotenv import load_dotenv

load_dotenv()


class PaymentService:
    def __init__(self):
        self.api_key = os.getenv("STRIPE_SECRET_KEY")
        if self.api_key is None:
            raise Exception("STRIPE_SECRET_KEY environment variable is not set.")
        stripe.api_key = self.api_key

    def create_payment_intent(self, amount: int, currency: str = "brl") -> dict:
        """
        Creates a Stripe PaymentIntent.

        Args:
            amount: The amount to charge, in the smallest currency unit (e.g., 100 for $1.00).
            currency: The currency of the payment. Defaults to "brl".

        Returns:
            A dictionary containing the client_secret if successful, or an error message.
        """
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                automatic_payment_methods={"enabled": True},
            )
            return {"client_secret": intent.client_secret}
        except stripe.error.CardError as e:
            # A card error occurred.
            return {"error": e.user_message}
        except stripe.error.RateLimitError as e:
            # Too many requests made to the API too quickly
            return {"error": "Too many requests to Stripe API. Please try again later."}
        except stripe.error.InvalidRequestError as e:
            # Invalid parameters were supplied to Stripe API
            return {"error": e.user_message}
        except stripe.error.AuthenticationError as e:
            # Authentication with Stripe's API failed
            # (maybe you changed API keys recently)
            return {
                "error": "Authentication with Stripe failed. Please check your API key."
            }
        except stripe.error.APIConnectionError as e:
            # Network communication with Stripe failed
            return {
                "error": "Network communication with Stripe failed. Please check your internet connection."
            }
        except stripe.error.StripeError as e:
            # Display a very generic error to the user, and maybe send
            # yourself an email
            return {
                "error": "An unexpected error occurred with Stripe. Please try again later."
            }
        except Exception as e:
            # Something else happened, completely unrelated to Stripe
            return {"error": f"An unexpected error occurred: {e}"}
