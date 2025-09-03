/**
 * SQLBot 聊天测试页面 JavaScript
 */

class ChatTestApp {
    constructor() {
        this.state = {
            token: null,
            dataSource: null,
            currentChatId: null,
            currentChatRecordId: null,
            isChatting: false,
            eventSource: null
        };
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.showSection('loginSection');
        this.updateDebugInfo();
    }
    
    bindEvents() {
        document.getElementById('loginBtn').addEventListener('click', () => this.handleLogin());
        document.getElementById('refreshDatasourceBtn').addEventListener('click', () => this.loadDataSources());
        document.getElementById('datasourceSelect').addEventListener('change', (e) => this.handleDataSourceChange(e));
        document.getElementById('sendBtn').addEventListener('click', () => this.handleChat());
        document.getElementById('questionInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.handleChat();
        });
        document.getElementById('cleanCurrentBtn').addEventListener('click', () => this.handleCleanCurrent());
        document.getElementById('cleanAllBtn').addEventListener('click', () => this.handleCleanAll());
        document.getElementById('resetBtn').addEventListener('click', () => this.handleReset());
    }
    
    async handleLogin() {
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value.trim();
        
        if (!username || !password) {
            this.showMessage('请输入用户名和密码', 'error');
            return;
        }
        
        this.showLoading(true);
        
        try {
            const response = await fetch('/api/test/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    username: username,
                    password: password,
                    createChat: true
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.state.token = result.data.accessToken;
                this.state.currentChatId = result.data.chatId;
                
                this.updateTokenStatus('success', '登录成功');
                this.showMessage('登录成功！', 'success');
                
                this.showSection('datasourceSection');
                this.loadDataSources();
                
            } else {
                this.showMessage(result.message || '登录失败', 'error');
            }
            
        } catch (error) {
            console.error('登录错误:', error);
            this.showMessage('登录失败: ' + error.message, 'error');
        } finally {
            this.showLoading(false);
            this.updateDebugInfo();
        }
    }
    
    async loadDataSources() {
        try {
            const response = await fetch('/api/test/datasources');
            const result = await response.json();
            
            if (result.success) {
                this.populateDataSourceSelect(result.data);
                this.showMessage('数据源加载成功', 'success');
            } else {
                this.showMessage(result.message || '加载数据源失败', 'error');
            }
            
        } catch (error) {
            console.error('加载数据源错误:', error);
            this.showMessage('加载数据源失败: ' + error.message, 'error');
        }
    }
    
    populateDataSourceSelect(dataSources) {
        const select = document.getElementById('datasourceSelect');
        select.innerHTML = '<option value="">请选择数据源...</option>';
        
        dataSources.forEach(ds => {
            const option = document.createElement('option');
            option.value = ds.id;
            option.textContent = `${ds.name} (${ds.type})`;
            option.dataset.datasource = JSON.stringify(ds);
            select.appendChild(option);
        });
    }
    
    handleDataSourceChange(event) {
        const selectedOption = event.target.selectedOptions[0];
        if (selectedOption.value) {
            const datasource = JSON.parse(selectedOption.dataset.datasource);
            this.state.dataSource = datasource;
            
            document.getElementById('datasourceName').textContent = datasource.name;
            document.getElementById('datasourceDesc').textContent = datasource.description || '无描述';
            
            this.showSection('chatSection');
            this.showSection('resultsSection');
            this.showSection('actionsSection');
            this.showSection('debugSection');
            
            this.showMessage(`已选择数据源: ${datasource.name}`, 'success');
        }
        
        this.updateDebugInfo();
    }
    
    async handleChat() {
        const question = document.getElementById('questionInput').value.trim();
        
        if (!question) {
            this.showMessage('请输入问题', 'error');
            return;
        }
        
        if (!this.state.dataSource) {
            this.showMessage('请先选择数据源', 'error');
            return;
        }
        
        this.state.isChatting = true;
        this.updateChatStatus('processing', '处理中...');
        this.showLoading(true);
        
        this.addChatMessage('user', question);
        
        try {
            await this.startStreamChat(question);
            
        } catch (error) {
            console.error('聊天错误:', error);
            this.showMessage('聊天失败: ' + error.message, 'error');
            this.addChatMessage('system', '❌ 聊天失败: ' + error.message);
        } finally {
            this.state.isChatting = false;
            this.updateChatStatus('ready', '就绪');
            this.showLoading(false);
            this.updateDebugInfo();
        }
    }
    
    async startStreamChat(question) {
        return new Promise((resolve, reject) => {
            if (this.state.eventSource) {
                this.state.eventSource.close();
            }
            
            const eventSource = new EventSource(`/api/test/chat?dbId=${this.state.dataSource.id}&question=${encodeURIComponent(question)}&chatId=${this.state.currentChatId}`);
            
            this.state.eventSource = eventSource;
            
            let recordId = null;
            let aiResponse = '';
            
            eventSource.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('SSE数据:', data);
                    
                    switch (data.type) {
                        case 'id':
                            recordId = data.id;
                            this.state.currentChatRecordId = recordId;
                            this.updateDebugInfo();
                            break;
                            
                        case 'start':
                            this.addChatMessage('ai', data.message);
                            break;
                            
                        case 'sql-result':
                            if (data.content) {
                                aiResponse += data.content;
                                this.updateLastAIMessage(aiResponse);
                            }
                            break;
                            
                        case 'sql':
                            if (data.content) {
                                this.addChatMessage('ai', `📊 SQL查询:\n\`\`\`sql\n${data.content}\n\`\`\``);
                            }
                            break;
                            
                        case 'chart-result':
                            if (data.content) {
                                aiResponse += data.content;
                                this.updateLastAIMessage(aiResponse);
                            }
                            break;
                            
                        case 'chart':
                            if (data.content) {
                                try {
                                    const chartConfig = JSON.parse(data.content);
                                    this.addChatMessage('ai', `📈 图表配置:\n\`\`\`json\n${JSON.stringify(chartConfig, null, 2)}\n\`\`\``);
                                } catch (e) {
                                    this.addChatMessage('ai', `📈 图表配置:\n${data.content}`);
                                }
                            }
                            break;
                            
                        case 'finish':
                            eventSource.close();
                            this.state.eventSource = null;
                            this.loadChatResults();
                            resolve();
                            break;
                            
                        case 'error':
                            this.addChatMessage('system', '❌ 错误: ' + data.message);
                            eventSource.close();
                            this.state.eventSource = null;
                            reject(new Error(data.message));
                            break;
                            
                        default:
                            console.log('未知SSE类型:', data.type);
                    }
                    
                } catch (error) {
                    console.error('解析SSE数据错误:', error);
                    this.addChatMessage('system', '❌ 数据解析错误: ' + error.message);
                }
            };
            
            eventSource.onerror = (error) => {
                console.error('SSE连接错误:', error);
                eventSource.close();
                this.state.eventSource = null;
                reject(new Error('SSE连接失败'));
            };
            
            setTimeout(() => {
                if (eventSource.readyState === EventSource.OPEN) {
                    eventSource.close();
                    this.state.eventSource = null;
                    reject(new Error('聊天超时'));
                }
            }, 30000);
        });
    }
    
    async loadChatResults() {
        if (!this.state.currentChatRecordId) return;
        
        try {
            const dataResponse = await fetch('/api/test/getData', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chatRecordId: this.state.currentChatRecordId
                })
            });
            
            const dataResult = await dataResponse.json();
            if (dataResult.success) {
                this.displayChatData(dataResult.data);
            }
            
            const recommendResponse = await fetch('/api/test/recommend', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chatRecordId: this.state.currentChatRecordId
                })
            });
            
            const recommendResult = await recommendResponse.json();
            if (recommendResult.success) {
                this.displayRecommendations(recommendResult.data);
            }
            
        } catch (error) {
            console.error('获取结果错误:', error);
            this.showMessage('获取结果失败: ' + error.message, 'error');
        }
    }
    
    displayChatData(data) {
        const dataContent = document.getElementById('dataContent');
        
        if (data && data.data) {
            dataContent.innerHTML = `
                <div class="data-item">
                    <h4>查询结果:</h4>
                    <pre>${JSON.stringify(data.data, null, 2)}</pre>
                </div>
            `;
        } else {
            dataContent.innerHTML = '<p class="placeholder">暂无数据</p>';
        }
    }
    
    displayRecommendations(recommendations) {
        const recommendationsDiv = document.getElementById('recommendations');
        
        if (recommendations && recommendations.recommendations && recommendations.recommendations.length > 0) {
            const html = recommendations.recommendations.map(rec => 
                `<div class="recommendation-item">${rec}</div>`
            ).join('');
            recommendationsDiv.innerHTML = html;
        } else {
            recommendationsDiv.innerHTML = '<p class="placeholder">暂无推荐问题</p>';
        }
    }
    
    addChatMessage(type, content) {
        const chatHistory = document.getElementById('chatHistory');
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${type}`;
        
        messageDiv.innerHTML = `
            <div class="message-content">
                <p>${content}</p>
            </div>
        `;
        
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight;
    }
    
    updateLastAIMessage(content) {
        const aiMessages = document.querySelectorAll('.chat-message.ai');
        if (aiMessages.length > 0) {
            const lastMessage = aiMessages[aiMessages.length - 1];
            lastMessage.querySelector('.message-content p').textContent = content;
        }
    }
    
    async handleCleanCurrent() {
        if (!this.state.currentChatId) {
            this.showMessage('没有可清理的聊天', 'info');
            return;
        }
        
        try {
            const response = await fetch('/api/test/clean', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    chatIds: [this.state.currentChatId]
                })
            });
            
            const result = await response.json();
            if (result.success) {
                this.showMessage('清理成功', 'success');
                this.clearChatHistory();
                this.state.currentChatId = null;
                this.state.currentChatRecordId = null;
                this.updateDebugInfo();
            } else {
                this.showMessage(result.message || '清理失败', 'error');
            }
            
        } catch (error) {
            console.error('清理错误:', error);
            this.showMessage('清理失败: ' + error.message, 'error');
        }
    }
    
    async handleCleanAll() {
        try {
            const response = await fetch('/api/test/clean', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            
            const result = await response.json();
            if (result.success) {
                this.showMessage('清理所有聊天成功', 'success');
                this.clearChatHistory();
                this.state.currentChatId = null;
                this.state.currentChatRecordId = null;
                this.updateDebugInfo();
            } else {
                this.showMessage(result.message || '清理失败', 'error');
            }
            
        } catch (error) {
            console.error('清理错误:', error);
            this.showMessage('清理失败: ' + error.message, 'error');
        }
    }
    
    handleReset() {
        if (this.state.eventSource) {
            this.state.eventSource.close();
            this.state.eventSource = null;
        }
        
        this.state = {
            token: null,
            dataSource: null,
            currentChatId: null,
            currentChatRecordId: null,
            isChatting: false,
            eventSource: null
        };
        
        this.clearChatHistory();
        this.updateTokenStatus('pending', '未登录');
        this.updateChatStatus('ready', '就绪');
        this.resetDataSourceDisplay();
        this.resetResultsDisplay();
        
        this.showSection('loginSection');
        this.hideSection('datasourceSection');
        this.hideSection('chatSection');
        this.hideSection('resultsSection');
        this.hideSection('actionsSection');
        this.hideSection('debugSection');
        
        this.updateDebugInfo();
        this.showMessage('页面已重置', 'info');
    }
    
    clearChatHistory() {
        const chatHistory = document.getElementById('chatHistory');
        chatHistory.innerHTML = `
            <div class="chat-message system">
                <div class="message-content">
                    <p>👋 欢迎使用SQLBot！请选择数据源后开始提问。</p>
                </div>
            </div>
        `;
    }
    
    resetDataSourceDisplay() {
        document.getElementById('datasourceSelect').innerHTML = '<option value="">请选择数据源...</option>';
        document.getElementById('datasourceName').textContent = '未选择';
        document.getElementById('datasourceDesc').textContent = '-';
    }
    
    resetResultsDisplay() {
        document.getElementById('dataContent').innerHTML = '<p class="placeholder">聊天完成后将显示数据内容</p>';
        document.getElementById('recommendations').innerHTML = '<p class="placeholder">聊天完成后将显示推荐问题</p>';
    }
    
    showSection(sectionId) {
        document.getElementById(sectionId).style.display = 'block';
    }
    
    hideSection(sectionId) {
        document.getElementById(sectionId).style.display = 'none';
    }
    
    updateTokenStatus(status, text) {
        const statusElement = document.getElementById('tokenStatus');
        const badge = statusElement.querySelector('.status-badge');
        badge.className = `status-badge status-${status}`;
        badge.textContent = text;
    }
    
    updateChatStatus(status, text) {
        const statusElement = document.getElementById('chatStatus');
        const badge = statusElement.querySelector('.status-badge');
        badge.className = `status-badge status-${status}`;
        badge.textContent = text;
    }
    
    showLoading(show) {
        document.getElementById('loadingOverlay').style.display = show ? 'flex' : 'none';
    }
    
    showMessage(message, type = 'info') {
        const toast = document.getElementById('messageToast');
        toast.textContent = message;
        toast.className = `message-toast ${type}`;
        toast.classList.add('show');
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
    
    updateDebugInfo() {
        document.getElementById('debugRecordId').textContent = this.state.currentChatRecordId || '-';
        document.getElementById('debugChatId').textContent = this.state.currentChatId || '-';
        document.getElementById('debugStatus').textContent = this.state.isChatting ? '聊天中' : '空闲';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ChatTestApp();
});
