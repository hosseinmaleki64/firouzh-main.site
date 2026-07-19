from django.core.exceptions import ValidationError

MAX_IMAGE_SIZE_MB = 6
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

MAX_IMAGES_PER_PRODUCT = 4


def validate_image_size(file):
    """
    هر عکس نباید بیشتر از ۶ مگابایت باشد.
    این validator روی فیلد ImageField مدل ProductImage قرار می‌گیرد،
    اما چون در ویوها گاهی مستقیم .create() صدا زده می‌شود (که validatorهای
    فیلد را اجرا نمی‌کند)، در views.py هم یک چک دستیِ مشابه انجام شده است.
    """
    if file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError(
            f"حجم عکس نباید بیشتر از {MAX_IMAGE_SIZE_MB} مگابایت باشد."
        )
