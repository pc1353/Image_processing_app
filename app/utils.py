from PIL import Image

def compress_and_save_image(image: Image.Image, output_path: str):
    """
    Compress the image to 50% quality and save it as JPEG.
    """
    if image.mode in ('RGBA', 'P'):
        image = image.convert('RGB')
    image.save(output_path, 'JPEG', quality=50)