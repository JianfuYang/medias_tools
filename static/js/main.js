// 下载进度检查
function checkProgress(videoId) {
    fetch(`/progress/${videoId}`)
        .then(response => response.json())
        .then(data => {
            const progressBar = document.querySelector(`#progress-${videoId} .progress-bar`);
            if (progressBar) {
                progressBar.style.width = `${data.progress}%`;
                progressBar.setAttribute('aria-valuenow', data.progress);
                progressBar.textContent = `${data.progress}%`;
            }
            
            if (data.progress < 100) {
                setTimeout(() => checkProgress(videoId), 1000);
            }
        })
        .catch(error => console.error('进度检查错误:', error));
}

// 批量下载进度检查
function checkBatchProgress(channelId) {
    fetch(`/batch/progress/${channelId}`)
        .then(response => response.json())
        .then(data => {
            const progressList = document.getElementById('progressList');
            if (!progressList) return;

            // 更新或创建进度条
            data.forEach(item => {
                let progressDiv = document.getElementById(`progress-${item.title}`);
                if (!progressDiv) {
                    progressDiv = document.createElement('div');
                    progressDiv.id = `progress-${item.title}`;
                    progressDiv.className = 'mb-3';
                    progressDiv.innerHTML = `
                        <div class="d-flex justify-content-between">
                            <span>${item.title}</span>
                            <span class="progress-text">0%</span>
                        </div>
                        <div class="progress">
                            <div class="progress-bar" role="progressbar" style="width: 0%"
                                 aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">0%</div>
                        </div>
                    `;
                    progressList.appendChild(progressDiv);
                }

                // 更新进度
                const progressBar = progressDiv.querySelector('.progress-bar');
                const progressText = progressDiv.querySelector('.progress-text');
                progressBar.style.width = `${item.progress}%`;
                progressBar.setAttribute('aria-valuenow', item.progress);
                progressBar.textContent = `${item.progress}%`;
                progressText.textContent = `${item.progress}%`;

                // 更新状态
                if (item.status === 'error') {
                    progressDiv.classList.add('text-danger');
                    progressText.textContent = `错误: ${item.error}`;
                }
            });

            // 如果还有未完成的下载，继续检查
            if (data.some(item => item.progress < 100 && item.status !== 'error')) {
                setTimeout(() => checkBatchProgress(channelId), 1000);
            }
        })
        .catch(error => console.error('批量下载进度检查错误:', error));
}

// 开始批量下载
function startBatchDownload(event) {
    event.preventDefault();
    const form = event.target;
    const channelUrl = form.querySelector('#channelUrl').value;
    const progressDiv = document.getElementById('downloadProgress');
    
    // 显示进度区域
    progressDiv.style.display = 'block';
    
    // 发送下载请求
    fetch('/batch/download', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ channel_url: channelUrl })
    })
    .then(response => response.json())
    .then(data => {
        // 提取频道ID
        const channelId = channelUrl.split('/').pop().replace('@', '');
        // 开始检查进度
        checkBatchProgress(channelId);
    })
    .catch(error => {
        console.error('下载请求错误:', error);
        alert('下载请求失败，请重试');
    });
}

// 页面加载完成后的初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化折叠面板
    const collapseElements = document.querySelectorAll('[data-toggle="collapse"]');
    collapseElements.forEach(element => {
        element.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-target'));
            if (target) {
                target.classList.toggle('show');
            }
        });
    });
}); 