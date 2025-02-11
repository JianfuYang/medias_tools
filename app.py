from flask import Flask, render_template, abort # type: ignore

app = Flask(__name__)

# 定义工具配置
TOOLS_CONFIG = {
    'ai-image': {
        'name': 'AI文生图',
        'features': [
            {
                'title': '智能生成',
                'desc': '通过文字描述智能生成高质量图像，支持多种风格和场景'
            },
            {
                'title': '风格调整',
                'desc': '提供丰富的风格预设和参数调整，实现个性化创作'
            },
            {
                'title': '批量导出',
                'desc': '支持批量生成和导出，满足批量创作需求'
            }
        ],
        'progress': 35
    },
    'text-card': {
        'name': '文字卡片生成',
        'features': [
            {
                'title': '模板系统',
                'desc': '提供丰富的卡片模板，快速创建精美文字卡片'
            },
            {
                'title': '样式定制',
                'desc': '支持自定义字体、颜色、布局等样式元素'
            },
            {
                'title': '一键分享',
                'desc': '支持导出多种格式，方便社交媒体分享'
            }
        ],
        'progress': 45
    },
    'image-compress': {
        'name': '图片压缩',
        'features': [
            {
                'title': '智能压缩',
                'desc': '自动优化压缩参数，在保证画质的同时最大程度减小文件体积'
            },
            {
                'title': '批量处理',
                'desc': '支持多图片同时处理，提高工作效率'
            },
            {
                'title': '格式优化',
                'desc': '根据使用场景推荐最佳图片格式'
            }
        ],
        'progress': 60
    },
    'resize': {
        'name': '调整大小',
        'features': [
            {
                'title': '精确调整',
                'desc': '支持精确的尺寸和比例调整，满足各种规格需求'
            },
            {
                'title': '智能裁剪',
                'desc': '智能识别图片主体，自动进行最优裁剪'
            },
            {
                'title': '批量处理',
                'desc': '支持批量调整图片尺寸，提高处理效率'
            }
        ],
        'progress': 50
    },
    'convert': {
        'name': '格式转换',
        'features': [
            {
                'title': '多格式支持',
                'desc': '支持常见图片格式之间的相互转换'
            },
            {
                'title': '参数优化',
                'desc': '针对不同格式自动优化转换参数'
            },
            {
                'title': '批量转换',
                'desc': '支持批量格式转换，提高工作效率'
            }
        ],
        'progress': 40
    },
    'svg-editor': {
        'name': 'SVG编辑器',
        'features': [
            {
                'title': '可视化编辑',
                'desc': '直观的可视化界面，轻松编辑SVG文件'
            },
            {
                'title': '代码同步',
                'desc': '实时预览SVG代码和效果，快速调整'
            },
            {
                'title': '优化导出',
                'desc': '支持SVG优化和多种格式导出'
            }
        ],
        'progress': 25
    }
}

# 首页路由
@app.route('/')
def index():
    # 传递当前路径为根路径，确保首页导航激活
    return render_template('index.html', current_tool='/')

# YouTube下载器路由
@app.route('/youtube')
def youtube():
    # 传递YouTube工具路径
    return render_template('youtube.html', current_tool='/youtube')

# 处理所有工具页面的路由
@app.route('/tools/<tool_name>')
def tool_page(tool_name):
    # 检查工具是否存在
    if tool_name not in TOOLS_CONFIG:
        # 404错误时也传递current_tool
        return render_template('404.html', current_tool=None), 404
        
    # 获取工具配置
    tool_config = TOOLS_CONFIG[tool_name]
    
    # 构建完整的工具路径
    tool_path = f'/tools/{tool_name}'
    
    # 传递工具配置和路径
    return render_template('developing.html', 
                         current_tool=tool_path,
                         tool_name=tool_config['name'],
                         features=tool_config['features'],
                         progress=tool_config['progress'])

# 404错误处理
@app.errorhandler(404)
def page_not_found(e):
    # 404错误时传递current_tool为None
    return render_template('404.html', current_tool=None), 404

if __name__ == '__main__':
    app.run(debug=True) 