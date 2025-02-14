class CodeDiffTool {
    constructor() {
        this.editor1 = null;
        this.editor2 = null;
        this.dmp = null;
    }

    static async create() {
        const instance = new CodeDiffTool();
        await instance.init();
        return instance;
    }

    async init() {
        try {
            this.showLoading();
            
            // 确保 diff_match_patch 已加载
            if (typeof window.diff_match_patch === 'undefined') {
                await new Promise((resolve) => {
                    const script = document.createElement('script');
                    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/diff-match-patch/20121119/diff_match_patch_uncompressed.js';
                    script.onload = resolve;
                    document.head.appendChild(script);
                });
            }

            // 初始化 diff_match_patch
            this.dmp = new diff_match_patch();
            this.dmp.Diff_Timeout = 1;
            this.dmp.Diff_EditCost = 4;

            // 等待 Monaco Editor 加载
            await this.waitForMonaco();
            
            await this.initEditors();
            this.initElements();
            this.bindEvents();
            
            this.hideLoading();
        } catch (error) {
            console.error('初始化失败:', error);
            this.showError('工具初始化失败：' + error.message);
        }
    }

    async waitForMonaco() {
        return new Promise((resolve, reject) => {
            let attempts = 0;
            const maxAttempts = 100;
            
            const checkMonaco = () => {
                attempts++;
                if (window.monaco && window.monaco.editor) {
                    resolve();
                } else if (attempts >= maxAttempts) {
                    reject(new Error('编辑器加载超时，请检查网络连接'));
                } else {
                    setTimeout(checkMonaco, 100);
                }
            };
            
            if (window.require) {
                require(['vs/editor/editor.main'], () => {
                    resolve();
                });
            } else {
                checkMonaco();
            }
        });
    }

    showLoading() {
        const containers = document.querySelectorAll('.editor-container');
        containers.forEach(container => {
            const loading = document.createElement('div');
            loading.className = 'editor-loading';
            loading.textContent = '编辑器加载中...';
            container.appendChild(loading);
        });
    }

    hideLoading() {
        document.querySelectorAll('.editor-loading').forEach(el => el.remove());
    }

    async initEditors() {
        try {
            // 确保容器存在
            const container1 = document.getElementById('editor1');
            const container2 = document.getElementById('editor2');
            
            if (!container1 || !container2) {
                throw new Error('找不到编辑器容器');
            }

            const editorConfig = {
                language: 'plaintext',
                theme: 'vs',
                minimap: { enabled: false },
                scrollBeyondLastLine: false,
                automaticLayout: true,
                fontSize: 14,
                lineNumbers: 'on',
                renderWhitespace: 'all',
                tabSize: 4,
                wordWrap: 'on',
                autoIndent: 'advanced',
                formatOnType: true,
                formatOnPaste: true,
                quickSuggestions: true,
                contextmenu: true,
                readOnly: false,
                bracketPairColorization: true,
                autoClosingBrackets: 'always',
                autoClosingQuotes: 'always',
                scrollbar: {
                    verticalScrollbarSize: 12,
                    horizontalScrollbarSize: 12,
                    alwaysConsumeMouseWheel: false
                }
            };

            // 确保 monaco 对象存在
            if (!window.monaco || !window.monaco.editor) {
                throw new Error('Monaco Editor 未正确加载');
            }

            // 创建编辑器实例前先清空容器
            container1.innerHTML = '';
            container2.innerHTML = '';

            // 创建编辑器实例
            this.editor1 = monaco.editor.create(container1, {
                ...editorConfig,
                value: '// 在此输入原始代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码'
            });

            this.editor2 = monaco.editor.create(container2, {
                ...editorConfig,
                value: '// 在此输入需要比较的代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码'
            });

            // 立即触发一次布局更新
            this.editor1.layout();
            this.editor2.layout();

            // 添加窗口大小变化时的自适应
            window.addEventListener('resize', () => {
                if (this.editor1 && this.editor2) {
                    this.editor1.layout();
                    this.editor2.layout();
                }
            });

            // 添加编辑器获得焦点时的处理
            this.editor1.onDidFocusEditorText(() => {
                const value = this.editor1.getValue();
                if (value.startsWith('// 在此输入原始代码')) {
                    this.editor1.setValue('');
                    // 设置光标位置到开始处
                    this.editor1.setPosition({lineNumber: 1, column: 1});
                }
            });

            this.editor2.onDidFocusEditorText(() => {
                const value = this.editor2.getValue();
                if (value.startsWith('// 在此输入需要比较的代码')) {
                    this.editor2.setValue('');
                    // 设置光标位置到开始处
                    this.editor2.setPosition({lineNumber: 1, column: 1});
                }
            });

            // 添加编辑器失去焦点且内容为空时的处理
            this.editor1.onDidBlurEditorText(() => {
                if (!this.editor1.getValue().trim()) {
                    this.editor1.setValue('// 在此输入原始代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码');
                }
            });

            this.editor2.onDidBlurEditorText(() => {
                if (!this.editor2.getValue().trim()) {
                    this.editor2.setValue('// 在此输入需要比较的代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码');
                }
            });

            // 确保编辑器正确加载
            if (!this.editor1 || !this.editor2) {
                throw new Error('编辑器初始化失败');
            }
        } catch (error) {
            throw new Error('编辑器初始化失败: ' + error.message);
        }
    }

    showError(message) {
        console.error(message);
        this.hideLoading(); // 出错时也要隐藏加载提示
        
        const errorDiv = document.createElement('div');
        errorDiv.className = 'p-4 bg-red-50 text-red-600 rounded-lg mt-4';
        errorDiv.textContent = message;
        
        // 移除之前的错误提示
        const oldError = document.querySelector('.bg-red-50');
        if (oldError) {
            oldError.remove();
        }
        
        // 添加新的错误提示
        const container = document.querySelector('.container');
        if (container) {
            container.insertBefore(errorDiv, container.firstChild);
        }
    }

    initElements() {
        this.elements = {
            language: document.getElementById('language'),
            showDiff: document.getElementById('showDiff'),
            showLineNumber: document.getElementById('showLineNumber'),
            ignoreCase: document.getElementById('ignoreCase'),
            ignoreSpace: document.getElementById('ignoreSpace'),
            compareBtn: document.getElementById('compareBtn'),
            clearBtn: document.getElementById('clearBtn'),
            diffView: document.getElementById('diffView'),
            diffResult: document.getElementById('diffResult'),
        };
    }

    bindEvents() {
        // 语言切换
        this.elements.language.addEventListener('change', () => {
            const language = this.elements.language.value;
            const config = this.getLanguageConfig(language);
            
            [this.editor1, this.editor2].forEach(editor => {
                monaco.editor.setModelLanguage(editor.getModel(), language);
                editor.updateOptions({
                    tabSize: config.tabSize,
                    insertSpaces: config.insertSpaces
                });
            });
            
            // 自动格式化代码
            setTimeout(() => {
                this.editor1.getAction('editor.action.formatDocument').run();
                this.editor2.getAction('editor.action.formatDocument').run();
            }, 100);
        });

        // 显示选项变化
        [
            this.elements.showDiff,
            this.elements.showLineNumber,
            this.elements.ignoreCase,
            this.elements.ignoreSpace
        ].forEach(el => {
            el.addEventListener('change', () => this.compare());
        });

        // 比较按钮
        this.elements.compareBtn.addEventListener('click', () => this.compare());

        // 清空按钮
        this.elements.clearBtn.addEventListener('click', () => this.clear());

        // 添加键盘快捷键
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter 触发比较
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.compare();
            }
            // Ctrl/Cmd + L 清空内容
            if ((e.ctrlKey || e.metaKey) && e.key === 'l') {
                e.preventDefault();
                this.clear();
            }
        });
    }

    compare() {
        try {
            if (!this.dmp) {
                throw new Error('比较工具未初始化');
            }

            const text1 = this.editor1.getValue();
            const text2 = this.editor2.getValue();

            // 检查输入内容
            if (!text1.trim() || !text2.trim()) {
                throw new Error('请在两个编辑器中都输入内容');
            }

            // 处理忽略选项
            let processedText1 = text1;
            let processedText2 = text2;

            if (this.elements.ignoreCase.checked) {
                processedText1 = processedText1.toLowerCase();
                processedText2 = processedText2.toLowerCase();
            }

            if (this.elements.ignoreSpace.checked) {
                processedText1 = processedText1.replace(/\s+/g, ' ').trim();
                processedText2 = processedText2.replace(/\s+/g, ' ').trim();
            }

            // 执行比较
            const diffs = this.dmp.diff_main(processedText1, processedText2);
            this.dmp.diff_cleanupSemantic(diffs);

            // 显示结果
            this.elements.diffView.classList.remove('hidden');
            this.elements.diffResult.innerHTML = '';
            this.showDiff(diffs);
        } catch (error) {
            console.error('比较失败:', error);
            this.showError('比较过程出现错误：' + error.message);
        }
    }

    showDiff(diffs) {
        this.elements.diffView.classList.remove('hidden');
        this.elements.diffResult.innerHTML = '';

        let lineNumber = 1;
        diffs.forEach(([type, text]) => {
            if (!text) return;

            const lines = text.split('\n');
            lines.forEach((line, index) => {
                const diffLine = document.createElement('div');
                diffLine.className = 'diff-line';

                // 添加行号
                if (this.elements.showLineNumber.checked) {
                    const lineNumberEl = document.createElement('div');
                    lineNumberEl.className = 'diff-line-number';
                    lineNumberEl.textContent = lineNumber;
                    diffLine.appendChild(lineNumberEl);
                }

                // 添加内容
                const content = document.createElement('div');
                content.className = 'diff-line-content';

                if (this.elements.showDiff.checked) {
                    switch (type) {
                        case 0:
                            content.classList.add('diff-unchanged');
                            break;
                        case 1:
                            content.classList.add('diff-added');
                            break;
                        case -1:
                            content.classList.add('diff-removed');
                            break;
                    }
                }

                if (lineNumber % 2 === 0) {
                    content.classList.add('diff-shadow');
                }

                content.textContent = line || ' ';
                diffLine.appendChild(content);

                this.elements.diffResult.appendChild(diffLine);
                lineNumber++;
            });
        });
    }

    clear() {
        this.editor1.setValue('// 在此输入原始代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码');
        this.editor2.setValue('// 在此输入需要比较的代码\n// 支持多种编程语言\n// 可以从其他编辑器复制粘贴代码');
        this.elements.diffView.classList.add('hidden');
        this.elements.diffResult.innerHTML = '';
        // 重置编辑器状态
        this.editor1.setPosition({lineNumber: 1, column: 1});
        this.editor2.setPosition({lineNumber: 1, column: 1});
    }

    getLanguageConfig(language) {
        const configs = {
            'javascript': {
                tabSize: 2,
                insertSpaces: true
            },
            'python': {
                tabSize: 4,
                insertSpaces: true
            },
            'java': {
                tabSize: 4,
                insertSpaces: true
            },
            'html': {
                tabSize: 2,
                insertSpaces: true
            },
            'css': {
                tabSize: 2,
                insertSpaces: true
            }
        };
        return configs[language] || { tabSize: 4, insertSpaces: true };
    }
}

// 修改初始化方式，确保在页面完全加载后再初始化
window.addEventListener('load', async () => {
    try {
        // 等待一小段时间确保所有资源加载完成
        await new Promise(resolve => setTimeout(resolve, 500));
        await CodeDiffTool.create();
    } catch (error) {
        console.error('初始化失败:', error);
        // 隐藏所有加载提示
        document.querySelectorAll('.editor-loading').forEach(el => el.remove());
        
        const container = document.querySelector('.container');
        if (container) {
            const errorDiv = document.createElement('div');
            errorDiv.className = 'p-4 bg-red-50 text-red-600 rounded-lg mt-4';
            errorDiv.textContent = '工具初始化失败，请刷新页面重试。';
            container.insertBefore(errorDiv, container.firstChild);
        }
    }
});
