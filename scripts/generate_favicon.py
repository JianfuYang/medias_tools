from cairosvg import svg2png
import os

# 确保输出目录存在
os.makedirs('static/images', exist_ok=True)

# 读取SVG文件
with open('static/images/logo.svg', 'rb') as svg_file:
    svg_data = svg_file.read()

# 生成不同尺寸的PNG
sizes = {
    'favicon.png': 32,
    'apple-touch-icon.png': 180
}

for filename, size in sizes.items():
    svg2png(bytestring=svg_data,
            write_to=f'static/images/{filename}',
            output_width=size,
            output_height=size) 