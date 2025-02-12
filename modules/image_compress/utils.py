import io
import base64
from PIL import Image

def create_preview_image(img, max_size=300):
    """创建预览图"""
    preview_img = img.copy()
    
    # 计算预览尺寸
    ratio = max_size / max(img.size)
    preview_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
    preview_img.thumbnail(preview_size)
    
    # 如果图片有透明通道，转换为RGB并使用白色背景
    if preview_img.mode == 'RGBA':
        # 创建白色背景
        background = Image.new('RGB', preview_img.size, (255, 255, 255))
        # 将原图与背景合并
        background.paste(preview_img, mask=preview_img.split()[3])  # 使用alpha通道作为mask
        preview_img = background
    elif preview_img.mode != 'RGB':
        # 其他颜色模式也转换为RGB
        preview_img = preview_img.convert('RGB')
    
    preview_buffer = io.BytesIO()
    preview_img.save(preview_buffer, format='JPEG', quality=85, optimize=True)
    return base64.b64encode(preview_buffer.getvalue()).decode() 