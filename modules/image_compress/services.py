from PIL import Image
import io
import base64
from .utils import create_preview_image
import logging
import os

logger = logging.getLogger(__name__)

def get_image_format(filename):
    """获取图片格式，统一格式名称"""
    ext = os.path.splitext(filename)[1].lower()
    format_map = {
        '.jpg': 'JPEG',
        '.jpeg': 'JPEG',
        '.png': 'PNG',
        '.webp': 'WEBP'
    }
    return format_map.get(ext, 'JPEG')

async def compress_image_service(file, quality, max_width, keep_exif):
    try:
        logger.info(f"开始处理图片: {file.filename}")
        logger.debug(f"参数: quality={quality}, max_width={max_width}, keep_exif={keep_exif}")
        
        # 验证文件类型
        if not file.content_type.startswith('image/'):
            raise Exception("只支持图片文件")
            
        # 验证参数
        if not isinstance(quality, int) or quality < 0 or quality > 100:
            raise Exception("质量参数必须在0-100之间")
            
        if max_width is not None:
            try:
                max_width = int(max_width)
                if max_width <= 0:
                    raise Exception("最大宽度必须大于0")
            except ValueError:
                raise Exception("最大宽度必须是有效的数字")

        # 读取上传的图片
        content = await file.read()
        if not content:
            raise Exception("文件内容为空")
            
        img = Image.open(io.BytesIO(content))
        original_mode = img.mode  # 保存原始颜色模式
        
        # 获取图片格式
        save_format = get_image_format(file.filename)
        logger.debug(f"图片格式: {save_format}, 颜色模式: {original_mode}")
        
        # 保存原始尺寸和创建预览图
        original_size = len(content)
        original_dimensions = img.size
        
        try:
            preview_base64 = create_preview_image(img)
        except Exception as e:
            logger.error(f"创建预览图失败: {str(e)}", exc_info=True)
            preview_base64 = ""  # 预览失败时使用空字符串
        
        # 如果指定了最大宽度，调整图片尺寸
        if max_width and img.size[0] > max_width:
            ratio = max_width / img.size[0]
            new_size = (max_width, int(img.size[1] * ratio))
            img = img.resize(new_size, Image.LANCZOS)
        
        # 准备压缩参数
        output = io.BytesIO()
        
        try:
            save_params = {
                'format': save_format,
                'optimize': True  # 启用优化
            }
            
            # 根据不同格式设置特定参数
            if save_format == 'JPEG':
                # 如果是RGBA模式，需要先转换为RGB
                if img.mode == 'RGBA':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                save_params.update({
                    'quality': quality,
                    'progressive': True,  # 启用渐进式JPEG
                    'optimize': True,
                    'subsampling': '4:2:0'  # 使用更高的压缩率
                })
                
                if keep_exif and 'exif' in img.info:
                    save_params['exif'] = img.info['exif']
                    
            elif save_format == 'PNG':
                if original_mode == 'RGBA':
                    # 保持透明通道
                    save_params.update({
                        'optimize': True,
                        'compress_level': 9,  # 最高压缩级别
                        'quantize': 256  # 减少颜色数量
                    })
                else:
                    # 如果原图没有透明通道，转换为RGB以减小文件大小
                    img = img.convert('RGB')
                    save_params.update({
                        'format': 'JPEG',  # 转换为JPEG以获得更好的压缩效果
                        'quality': quality,
                        'optimize': True,
                        'progressive': True
                    })
                    
            elif save_format == 'WEBP':
                save_params.update({
                    'quality': quality,
                    'method': 6,  # 最高压缩质量
                    'lossless': img.mode == 'RGBA',  # 对于带透明度的图片使用无损压缩
                    'exact': True  # 保持透明度
                })
            
            # 保存图片
            img.save(output, **save_params)
            
        except Exception as e:
            logger.error(f"保存图片失败: {str(e)}", exc_info=True)
            raise Exception(f"保存图片失败: {str(e)}")
        
        # 获取压缩后的数据
        compressed_data = output.getvalue()
        compressed_size = len(compressed_data)
        compressed_base64 = base64.b64encode(compressed_data).decode()
        
        # 计算压缩率 - 修正计算方法
        # 压缩率 = (原始大小 - 压缩后大小) / 原始大小 * 100
        if original_size > 0:  # 防止除以零
            reduction = round((1 - compressed_size / original_size) * 100, 2)
            # 确保压缩率不为负数
            reduction = max(0, reduction)
        else:
            reduction = 0
            
        logger.info(f"图片处理完成: {file.filename}")
        logger.debug(f"压缩结果: 原始大小={original_size}, 压缩后大小={compressed_size}, 压缩率={reduction}%")
        
        # 添加更详细的日志
        if reduction <= 0:
            logger.warning(f"压缩效果不理想: {file.filename}, 原始大小={original_size}, 压缩后大小={compressed_size}")
        
        return {
            "success": True,
            "original": {
                "size": original_size,
                "width": original_dimensions[0],
                "height": original_dimensions[1],
                "preview": f"data:image/jpeg;base64,{preview_base64}"
            },
            "compressed": {
                "size": compressed_size,
                "width": img.size[0],
                "height": img.size[1],
                "data": f"data:image/{save_format.lower()};base64,{compressed_base64}"
            },
            "reduction": reduction,
            "format": save_format.lower()
        }
    except Exception as e:
        logger.error(f"图片压缩失败: {str(e)}", exc_info=True)
        raise 