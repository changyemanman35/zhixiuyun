/**
 * 售后工单管理系统 (ASM) - 企业级自研原生交互组件库 (app.js)
 * 严格遵循 NFR-6 纯离线原则：零外部 CDN、零第三方依赖，纯原生 Vanilla JavaScript 手写构建
 */

(function () {
    'use strict';

    // ── 1. 全局 Toast 消息通知队列组件 ──
    const Toast = {
        container: null,
        init() {
            if (!this.container) {
                this.container = document.getElementById('toast-container');
                if (!this.container) {
                    this.container = document.createElement('div');
                    this.container.id = 'toast-container';
                    document.body.appendChild(this.container);
                }
            }
        },
        show(title, message, type = 'info', duration = 3500) {
            this.init();
            const item = document.createElement('div');
            item.className = `toast-item toast-${type}`;

            const iconMap = {
                success: '✓',
                danger: '✕',
                warning: '⚠',
                info: 'ℹ'
            };

            item.innerHTML = `
                <div class="toast-body">
                    <div class="toast-icon">${iconMap[type] || 'ℹ'}</div>
                    <div class="toast-content">
                        <div class="toast-title">${title}</div>
                        <div class="toast-message">${message}</div>
                    </div>
                    <div class="toast-close">×</div>
                </div>
                <div class="toast-progress">
                    <div class="toast-progress-bar"></div>
                </div>
            `;

            this.container.appendChild(item);

            // 触发滑入动画
            requestAnimationFrame(() => {
                item.classList.add('toast-show');
                const bar = item.querySelector('.toast-progress-bar');
                if (bar) {
                    bar.style.transitionDuration = `${duration}ms`;
                    bar.style.width = '0%';
                }
            });

            // 自动关闭与手动关闭
            let timer = setTimeout(() => this.remove(item), duration);

            item.querySelector('.toast-close').addEventListener('click', () => {
                clearTimeout(timer);
                this.remove(item);
            });
        },
        remove(item) {
            item.classList.remove('toast-show');
            setTimeout(() => {
                if (item.parentNode) {
                    item.parentNode.removeChild(item);
                }
            }, 300);
        }
    };
    window.Toast = Toast;

    // 自动将后端 flash 消息接管渲染为 Toast
    document.addEventListener('DOMContentLoaded', () => {
        const flashes = document.querySelectorAll('.flash-message-hidden');
        flashes.forEach(f => {
            const type = f.dataset.category || 'info';
            const msg = f.textContent.trim();
            if (msg) {
                Toast.show(type === 'error' || type === 'danger' ? '系统提示' : '操作成功', msg, type === 'error' ? 'danger' : type);
            }
        });
    });

    // ── 2. 原生 HTML5 拖拽看板与多维过滤胶囊 ──
    window.initKanban = function () {
        const cards = document.querySelectorAll('.kanban-card[draggable="true"]');
        const columns = document.querySelectorAll('.kanban-column');
        const chips = document.querySelectorAll('.filter-chip');
        const searchInput = document.getElementById('kanban-search-input');

        // 拖拽流转
        cards.forEach(card => {
            card.addEventListener('dragstart', (e) => {
                card.classList.add('dragging');
                e.dataTransfer.setData('text/plain', card.dataset.orderId);
                e.dataTransfer.effectAllowed = 'move';
            });

            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                columns.forEach(col => col.classList.remove('drag-over-active'));
            });
        });

        columns.forEach(col => {
            col.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                col.classList.add('drag-over-active');
            });

            col.addEventListener('dragleave', () => {
                col.classList.remove('drag-over-active');
            });

            col.addEventListener('drop', (e) => {
                e.preventDefault();
                col.classList.remove('drag-over-active');
                const orderId = e.dataTransfer.getData('text/plain');
                const targetStatus = col.dataset.status;
                const draggingCard = document.querySelector(`.kanban-card[data-order-id="${orderId}"]`);

                if (draggingCard && targetStatus) {
                    const fromStatus = draggingCard.dataset.status;
                    if (fromStatus === targetStatus) return;

                    // 检查合法流转并给出交互反馈
                    Toast.show('敏捷看板', `已捕捉工单 #${orderId} 状态变更意图：${fromStatus} ➔ ${targetStatus}。请点击详情卡片核验派工/处理。`, 'info');
                }
            });
        });

        // 多维即时过滤胶囊
        function applyFilter() {
            const activeChip = document.querySelector('.filter-chip.active');
            const filterType = activeChip ? activeChip.dataset.filter : 'all';
            const keyword = (searchInput ? searchInput.value : '').toLowerCase().trim();

            document.querySelectorAll('.kanban-card').forEach(card => {
                let matchFilter = true;
                if (filterType === 'urgent') {
                    matchFilter = card.dataset.priority === 'urgent';
                } else if (filterType === 'rework') {
                    matchFilter = card.dataset.rework === 'true';
                } else if (filterType === 'warn') {
                    matchFilter = card.dataset.sla === 'warn' || card.dataset.sla === 'danger';
                } else if (filterType === 'warranty') {
                    matchFilter = card.dataset.warranty === 'true';
                }

                let matchKeyword = true;
                if (keyword) {
                    const text = card.textContent.toLowerCase();
                    matchKeyword = text.includes(keyword);
                }

                card.style.display = (matchFilter && matchKeyword) ? 'block' : 'none';
            });
        }

        chips.forEach(chip => {
            chip.addEventListener('click', () => {
                chips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                applyFilter();
            });
        });

        if (searchInput) {
            searchInput.addEventListener('input', applyFilter);
        }
    };

    // ── 3. 四步向导式报修步进器 (Stepper Wizard) ──
    window.initStepperWizard = function () {
        const steps = document.querySelectorAll('.stepper-step');
        const panels = document.querySelectorAll('.wizard-panel');
        if (!steps.length) return;

        window.goToStep = function (stepIndex) {
            steps.forEach((s, idx) => {
                s.classList.remove('active');
                if (idx < stepIndex) s.classList.add('completed');
                else s.classList.remove('completed');
                if (idx === stepIndex) s.classList.add('active');
            });

            panels.forEach((p, idx) => {
                p.classList.remove('active');
                if (idx === stepIndex) p.classList.add('active');
            });
        };
    };

    // ── 4. 本地图片文件预览上传器 ──
    window.initFileUploader = function (dropzoneId, inputId, previewGridId) {
        const dropzone = document.getElementById(dropzoneId);
        const input = document.getElementById(inputId);
        const grid = document.getElementById(previewGridId);
        if (!dropzone || !input || !grid) return;

        dropzone.addEventListener('click', () => input.click());

        input.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            files.forEach(file => {
                if (!file.type.startsWith('image/')) {
                    Toast.show('格式错误', '仅支持上传 PNG、JPG 格式图片凭据', 'warning');
                    return;
                }
                if (file.size > 5 * 1024 * 1024) {
                    Toast.show('体积超限', '单张凭据照片不可超过 5MB', 'warning');
                    return;
                }

                const reader = new FileReader();
                reader.onload = (event) => {
                    const thumb = document.createElement('div');
                    thumb.className = 'preview-thumb-box';
                    thumb.innerHTML = `
                        <img src="${event.target.result}" class="preview-thumb-img" alt="故障凭证" />
                        <div class="preview-thumb-delete">×</div>
                    `;
                    thumb.querySelector('.preview-thumb-delete').addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        thumb.remove();
                    });
                    grid.appendChild(thumb);
                };
                reader.readAsDataURL(file);
            });
        });
    };

    // ── 5. 交互式五星评分与标签云 ──
    window.initStarRating = function (containerId, inputId, tagsContainerId, tagInputId) {
        const container = document.getElementById(containerId);
        const input = document.getElementById(inputId);
        if (!container || !input) return;

        const stars = container.querySelectorAll('.rating-star');
        let currentRating = parseInt(input.value || 5);

        function renderStars(rating, isHover = false) {
            stars.forEach((star, idx) => {
                if (idx < rating) {
                    star.classList.add(isHover ? 'hover' : 'active');
                } else {
                    star.classList.remove(isHover ? 'hover' : 'active');
                }
            });
        }

        renderStars(currentRating);

        stars.forEach((star, idx) => {
            star.addEventListener('mouseenter', () => renderStars(idx + 1, true));
            star.addEventListener('mouseleave', () => {
                stars.forEach(s => s.classList.remove('hover'));
                renderStars(currentRating);
            });
            star.addEventListener('click', () => {
                currentRating = idx + 1;
                input.value = currentRating;
                renderStars(currentRating);
                Toast.show('评分已设定', `已选择 ${currentRating} 星服务满意度`, 'info');
            });
        });

        // 标签云交互
        const tagBox = document.getElementById(tagsContainerId);
        const tagInput = document.getElementById(tagInputId);
        if (tagBox && tagInput) {
            const selectedTags = new Set();
            tagBox.querySelectorAll('.tag-cloud-item').forEach(item => {
                item.addEventListener('click', () => {
                    const tag = item.textContent.trim();
                    if (selectedTags.has(tag)) {
                        selectedTags.delete(tag);
                        item.classList.remove('selected');
                    } else {
                        selectedTags.add(tag);
                        item.classList.add('selected');
                    }
                    tagInput.value = Array.from(selectedTags).join(',');
                });
            });
        }
    };

    // ── 6. ASM Copilot 悬浮唤醒球与侧边抽屉 ──
    window.initCopilot = function () {
        const bubble = document.getElementById('copilot-bubble');
        const drawer = document.getElementById('copilot-drawer');
        const backdrop = document.getElementById('copilot-backdrop');
        const closeBtn = document.getElementById('copilot-close');
        const sendBtn = document.getElementById('copilot-send');
        const input = document.getElementById('copilot-input');
        const chatList = document.getElementById('copilot-chat-list');
        const suggestionBox = document.getElementById('copilot-suggestions');

        if (!bubble || !drawer) return;

        function openDrawer() {
            drawer.classList.add('drawer-open');
            if (backdrop) backdrop.classList.add('drawer-open');
            if (input) input.focus();
        }

        function closeDrawer() {
            drawer.classList.remove('drawer-open');
            if (backdrop) backdrop.classList.remove('drawer-open');
        }

        bubble.addEventListener('click', openDrawer);
        if (closeBtn) closeBtn.addEventListener('click', closeDrawer);
        if (backdrop) backdrop.addEventListener('click', closeDrawer);

        function appendMessage(sender, text, actions = []) {
            const bubbleDiv = document.createElement('div');
            bubbleDiv.className = `chat-bubble ${sender}`;
            bubbleDiv.innerHTML = text.replace(/\n/g, '<br/>');

            if (actions && actions.length > 0) {
                const actionWrap = document.createElement('div');
                actionWrap.style.marginTop = '10px';
                actionWrap.style.display = 'flex';
                actionWrap.style.gap = '8px';
                actions.forEach(act => {
                    const btn = document.createElement('a');
                    btn.href = act.url;
                    btn.className = `btn btn-sm ${act.primary ? 'btn-primary' : 'btn-default'}`;
                    btn.textContent = act.label;
                    actionWrap.appendChild(btn);
                });
                bubbleDiv.appendChild(actionWrap);
            }

            chatList.appendChild(bubbleDiv);
            chatList.scrollTop = chatList.scrollHeight;
        }

        async function handleSend(promptText) {
            const text = promptText || (input ? input.value.trim() : '');
            if (!text) return;
            if (input) input.value = '';

            appendMessage('user', text);

            try {
                const res = await fetch('/api/copilot/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        message: text,
                        context_page: window.location.pathname
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    appendMessage('assistant', data.reply, data.actions);

                    // 刷新建议提示词
                    if (suggestionBox && data.suggestions) {
                        suggestionBox.innerHTML = '';
                        data.suggestions.forEach(sug => {
                            const sugBtn = document.createElement('span');
                            sugBtn.className = 'filter-chip';
                            sugBtn.textContent = sug;
                            sugBtn.addEventListener('click', () => handleSend(sug));
                            suggestionBox.appendChild(sugBtn);
                        });
                    }
                } else {
                    appendMessage('assistant', data.reply || '系统响应异常，请稍后重试。');
                }
            } catch (err) {
                appendMessage('assistant', '网络连接不可用或本地离线保底服务异常。');
            }
        }

        if (sendBtn) sendBtn.addEventListener('click', () => handleSend());
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') handleSend();
            });
        }

        // 绑定预置引导词
        document.querySelectorAll('.copilot-preset-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                openDrawer();
                handleSend(btn.textContent.trim());
            });
        });
    };

    // ── 5. Aceternity UI 风格 Spotlight 鼠标跟随流光引擎 ──
    window.initSpotlight = function () {
        const cards = document.querySelectorAll('[data-spotlight]');
        cards.forEach(card => {
            card.addEventListener('mousemove', (e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty('--spotlight-x', `${x}px`);
                card.style.setProperty('--spotlight-y', `${y}px`);
                card.style.setProperty('--spotlight-opacity', '1');
            });
            card.addEventListener('mouseleave', () => {
                card.style.setProperty('--spotlight-opacity', '0');
            });
        });
    };

    // ── 6. 3D Spatial 视差悬浮倾斜引擎 (Vanilla Tilt 3D) ──
    window.initTilt3D = function () {
        const cards = document.querySelectorAll('[data-tilt]');
        cards.forEach(card => {
            let isHovered = false;
            card.addEventListener('mouseenter', () => {
                isHovered = true;
                card.style.transition = 'transform 0.1s ease-out';
            });
            card.addEventListener('mousemove', (e) => {
                if (!isHovered) return;
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const centerX = rect.width / 2;
                const centerY = rect.height / 2;
                const rotateX = -((y - centerY) / centerY) * 7;
                const rotateY = ((x - centerX) / centerX) * 7;
                card.style.transform = `perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) scale3d(1.02, 1.02, 1.02)`;
            });
            card.addEventListener('mouseleave', () => {
                isHovered = false;
                card.style.transition = 'transform 0.4s cubic-bezier(0.16, 1, 0.3, 1)';
                card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) scale3d(1, 1, 1)';
            });
        });
    };

    // ── 7. HTML5 Canvas 交互式星空光网粒子引擎 (Interactive Constellation) ──
    window.initHeroCanvas = function () {
        const canvas = document.getElementById('hero-particle-canvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        let width = canvas.clientWidth;
        let height = canvas.clientHeight;
        const dpr = window.devicePixelRatio || 1;

        function resize() {
            width = canvas.clientWidth;
            height = canvas.clientHeight;
            canvas.width = width * dpr;
            canvas.height = height * dpr;
            ctx.scale(dpr, dpr);
        }
        resize();
        window.addEventListener('resize', resize);

        const particles = [];
        const particleCount = Math.min(Math.floor(width / 22), 65);
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: Math.random() * width,
                y: Math.random() * height,
                vx: (Math.random() - 0.5) * 0.7,
                vy: (Math.random() - 0.5) * 0.7,
                radius: Math.random() * 2 + 1,
                color: i % 3 === 0 ? 'rgba(114, 46, 209, 0.65)' : 'rgba(22, 119, 255, 0.55)'
            });
        }

        let mouse = { x: null, y: null };
        canvas.parentElement.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.x = e.clientX - rect.left;
            mouse.y = e.clientY - rect.top;
        });
        canvas.parentElement.addEventListener('mouseleave', () => {
            mouse.x = null;
            mouse.y = null;
        });

        function animate() {
            ctx.clearRect(0, 0, width, height);

            // 更新并绘制粒子
            for (let i = 0; i < particles.length; i++) {
                const p = particles[i];
                p.x += p.vx;
                p.y += p.vy;

                if (p.x < 0 || p.x > width) p.vx *= -1;
                if (p.y < 0 || p.y > height) p.vy *= -1;

                // 鼠标微引力
                if (mouse.x !== null && mouse.y !== null) {
                    const dx = mouse.x - p.x;
                    const dy = mouse.y - p.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 120) {
                        p.x += dx * 0.015;
                        p.y += dy * 0.015;
                    }
                }

                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fillStyle = p.color;
                ctx.fill();

                // 绘制粒子间连线
                for (let j = i + 1; j < particles.length; j++) {
                    const p2 = particles[j];
                    const dx = p.x - p2.x;
                    const dy = p.y - p2.y;
                    const dist = Math.sqrt(dx * dx + dy * dy);
                    if (dist < 110) {
                        ctx.beginPath();
                        ctx.strokeStyle = `rgba(22, 119, 255, ${(1 - dist / 110) * 0.22})`;
                        ctx.lineWidth = 0.8;
                        ctx.moveTo(p.x, p.y);
                        ctx.lineTo(p2.x, p2.y);
                        ctx.stroke();
                    }
                }
            }

            requestAnimationFrame(animate);
        }
        animate();
    };

    // ── 8. 数字滚动跃升引擎 (CountUp Motion Engine) ──
    window.initCountUp = function () {
        const counters = document.querySelectorAll('[data-countup]');
        if (!counters.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const target = parseFloat(el.getAttribute('data-countup'));
                    const duration = parseInt(el.getAttribute('data-duration') || '1600', 10);
                    const decimals = parseInt(el.getAttribute('data-decimals') || '0', 10);
                    const prefix = el.getAttribute('data-prefix') || '';
                    const suffix = el.getAttribute('data-suffix') || '';

                    const startTime = performance.now();

                    function updateNumber(now) {
                        const elapsed = now - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        // easeOutQuad 缓动函数
                        const ease = 1 - (1 - progress) * (1 - progress);
                        const current = (ease * target).toFixed(decimals);
                        el.textContent = `${prefix}${current}${suffix}`;

                        if (progress < 1) {
                            requestAnimationFrame(updateNumber);
                        } else {
                            el.textContent = `${prefix}${target.toFixed(decimals)}${suffix}`;
                        }
                    }

                    requestAnimationFrame(updateNumber);
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.2 });

        counters.forEach(c => observer.observe(c));
    };

    // ── 9. PCB 精密硬件电路板微电流动态走线引擎 (PCB Trace Engine) ──
    window.initPCBTraces = function () {
        const traces = document.querySelectorAll('.pcb-trace-glow');
        if (!traces.length) return;
        traces.forEach((trace, idx) => {
            const length = trace.getTotalLength ? trace.getTotalLength() : 300;
            trace.style.strokeDasharray = `${length}`;
            trace.style.strokeDashoffset = `${length}`;
            trace.style.animation = `pcbDrawPulse 3.5s cubic-bezier(0.4, 0, 0.2, 1) infinite ${idx * 0.4}s`;
        });
    };

    // ── 10. 一物一码芯片全息激光扫码器动效 (Chip Hologram Scanner) ──
    window.initHologramScanner = function () {
        const scannerBox = document.getElementById('hologram-scanner-box');
        if (!scannerBox) return;
        const codeEl = document.getElementById('hologram-dynamic-hash');
        if (!codeEl) return;

        const hexChars = '0123456789ABCDEF';
        setInterval(() => {
            let hash = 'SN-2026-';
            for (let i = 0; i < 8; i++) {
                hash += hexChars[Math.floor(Math.random() * hexChars.length)];
            }
            codeEl.textContent = hash;
        }, 2200);
    };

    // ── 11. 售后故障与元器件透视交互工作台 (Interactive Triaging Workbench) ──
    window.initTriagingWorkbench = function () {
        const symptomChips = document.querySelectorAll('.triaging-chip');
        const targetPartName = document.getElementById('triaging-part-name');
        const targetPartSpec = document.getElementById('triaging-part-spec');
        const targetSop = document.getElementById('triaging-sop');
        const targetEstFee = document.getElementById('triaging-est-fee');

        if (!symptomChips.length || !targetPartName) return;

        symptomChips.forEach(chip => {
            chip.addEventListener('click', () => {
                symptomChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');

                const part = chip.getAttribute('data-part') || '原厂主控元器件';
                const spec = chip.getAttribute('data-spec') || '原装正品 · 一物一码';
                const sop = chip.getAttribute('data-sop') || '标准防静电无损拆装';
                const fee = chip.getAttribute('data-fee') || '¥130.00';

                targetPartName.textContent = part;
                targetPartSpec.textContent = spec;
                targetSop.textContent = sop;
                targetEstFee.textContent = fee;

                // 闪烁高亮提示
                targetPartName.parentElement.classList.add('triaging-flash');
                setTimeout(() => {
                    targetPartName.parentElement.classList.remove('triaging-flash');
                }, 400);
            });
        });
    };

    // ── 12. 真实家电售后维修 Canvas 60fps 双模视差引擎 (常态环境微动 + 滚轮推轨沉浸纪实) ──
    window.initPortalCanvasScrolly = function () {
        const canvas = document.getElementById('hero-scrolly-canvas');
        const track = document.getElementById('video-scrolly-track');
        if (!canvas || !track) return;

        const ctx = canvas.getContext('2d');
        const TOTAL_FRAMES = 120;
        const frames = [];

        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            renderFrame(currentProgress);
        }
        window.addEventListener('resize', resizeCanvas);

        // 预加载真实民生家电售后推轨序列帧
        for (let i = 0; i < TOTAL_FRAMES; i++) {
            const img = new Image();
            const pad = String(i).padStart(3, '0');
            img.src = `/static/frames/home_repair/frame_${pad}.jpg`;
            frames.push(img);
        }

        let targetProgress = 0;
        let currentProgress = 0;
        let isUserScrolling = false;
        let scrollTimeout = null;
        let ambientTime = 0;

        // 统一绘制函数 (0 延迟极速 cover 绘制)
        function renderFrame(prog) {
            if (!frames.length) return;
            const frameIndex = Math.min(TOTAL_FRAMES - 1, Math.max(0, Math.floor(prog * (TOTAL_FRAMES - 1))));
            const img = frames[frameIndex];
            if (img && img.complete && img.naturalWidth > 0) {
                const cW = canvas.width;
                const cH = canvas.height;
                const imgW = img.naturalWidth;
                const imgH = img.naturalHeight;
                const scale = Math.max(cW / imgW, cH / imgH);
                const drawW = imgW * scale;
                const drawH = imgH * scale;
                const drawX = (cW - drawW) / 2;
                const drawY = (cH - drawH) / 2;

                ctx.drawImage(img, drawX, drawY, drawW, drawH);
            }
        }

        // 常态环境微动与滚轮阻尼驱动主循环 (模拟录屏中如海浪一般一直在动的写实大片质感)
        function masterLoop() {
            ambientTime += 0.025;

            // 当用户没有剧烈滚动时，叠加自然微动 (Idle Ambient Micro-Motion)
            let effectiveProg = currentProgress;
            if (currentProgress < 0.15 && !isUserScrolling) {
                // 在未滚动时，如海浪拍打般自然微动起伏 (0.00 ~ 0.05 之间柔和正弦呼吸)
                const wave = (Math.sin(ambientTime) + 1) * 0.5 * 0.05;
                effectiveProg = Math.max(0, currentProgress + wave);
            } else if (!isUserScrolling) {
                // 在停驻深度，维持细微的呼吸微动 (±0.008)
                const subWave = Math.sin(ambientTime * 1.5) * 0.008;
                effectiveProg = Math.min(1, Math.max(0, currentProgress + subWave));
            }

            // 滚轮阻尼平滑插值 (LERP)
            currentProgress += (targetProgress - currentProgress) * 0.15;
            renderFrame(effectiveProg);

            // 前景文案淡出与位移
            const heroContent = document.getElementById('scrolly-hero-content');
            const exploreBadge = document.getElementById('scroll-to-explore-badge');
            if (heroContent) {
                if (currentProgress < 0.55) {
                    const alpha = Math.max(0, 1 - currentProgress * 1.9);
                    const translateY = -currentProgress * 65;
                    heroContent.style.opacity = `${alpha}`;
                    heroContent.style.transform = `translateY(${translateY}px)`;
                    heroContent.style.pointerEvents = alpha < 0.2 ? 'none' : 'auto';
                } else {
                    heroContent.style.opacity = '0';
                    heroContent.style.pointerEvents = 'none';
                }
            }

            if (exploreBadge) {
                exploreBadge.style.opacity = `${Math.max(0, 1 - currentProgress * 3.5)}`;
            }

            // 现场检修 HUD 数据面板浮现 (滚轮推进到 38%~92% 时显现)
            const deepHud = document.getElementById('scrolly-deep-hud');
            if (deepHud) {
                if (currentProgress >= 0.38 && currentProgress <= 0.92) {
                    const hudAlpha = Math.min(1, (currentProgress - 0.38) * 4);
                    deepHud.style.opacity = `${hudAlpha}`;
                    deepHud.style.transform = `translate(-50%, ${-(currentProgress - 0.38) * 30}px)`;
                } else {
                    deepHud.style.opacity = '0';
                }
            }

            requestAnimationFrame(masterLoop);
        }

        function onScroll() {
            isUserScrolling = true;
            if (scrollTimeout) clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                isUserScrolling = false;
            }, 300);

            const rect = track.getBoundingClientRect();
            const scrollDistance = -rect.top;
            const maxScroll = rect.height - window.innerHeight;
            if (maxScroll <= 0) return;

            targetProgress = Math.min(Math.max(scrollDistance / maxScroll, 0), 1);
        }

        window.addEventListener('scroll', onScroll, { passive: true });
        resizeCanvas();

        // 首帧加载完成后立即渲染并启动主循环
        if (frames[0]) {
            frames[0].onload = () => renderFrame(0);
        }
        setTimeout(() => renderFrame(0), 100);
        requestAnimationFrame(masterLoop);
    };
        onScroll();
    };

    // ── 13. 民生便民家电维修专属落地页：Canvas 60fps 逐帧双缓冲极速视差引擎 ──
    window.initHomeRepairPage = function () {
        const canvas = document.getElementById('home-scrolly-canvas');
        const track = document.getElementById('home-scrolly-track');
        if (!canvas || !track) return;

        const ctx = canvas.getContext('2d');
        const TOTAL_FRAMES = 120;
        let currentMode = 'appliance'; // 'appliance' 或 'ocean'

        // 内存图片池字典
        const framePools = {
            appliance: [],
            ocean: []
        };

        // 统一画布物理分辨率
        function resizeCanvas() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            renderCurrentFrame();
        }
        window.addEventListener('resize', resizeCanvas);

        // 异步预加载图片序列进内存池
        function preloadFrames(mode, prefixPath) {
            for (let i = 0; i < TOTAL_FRAMES; i++) {
                const img = new Image();
                const pad = String(i).padStart(3, '0');
                img.src = `${prefixPath}/frame_${pad}.jpg`;
                framePools[mode].push(img);
            }
        }

        // 启动预加载两大高精序列帧池
        preloadFrames('appliance', '/static/frames/appliance');
        preloadFrames('ocean', '/static/frames/ocean');

        let targetProgress = 0;
        let currentProgress = 0;
        let rafId = null;

        // 渲染单帧 (0延迟，不足 1ms 瞬时执行)
        function renderCurrentFrame() {
            const list = framePools[currentMode];
            if (!list || !list.length) return;

            const frameIndex = Math.min(TOTAL_FRAMES - 1, Math.max(0, Math.floor(currentProgress * (TOTAL_FRAMES - 1))));
            const img = list[frameIndex];
            if (img && img.complete && img.naturalWidth > 0) {
                // 等比例 cover 绘制
                const cW = canvas.width;
                const cH = canvas.height;
                const imgW = img.naturalWidth;
                const imgH = img.naturalHeight;
                const scale = Math.max(cW / imgW, cH / imgH);
                const drawW = imgW * scale;
                const drawH = imgH * scale;
                const drawX = (cW - drawW) / 2;
                const drawY = (cH - drawH) / 2;

                ctx.drawImage(img, drawX, drawY, drawW, drawH);
            }
        }

        // 模式切换器响应
        const btnAppliance = document.getElementById('btn-mode-appliance');
        const btnOcean = document.getElementById('btn-mode-ocean');
        if (btnAppliance && btnOcean) {
            btnAppliance.addEventListener('click', () => {
                btnAppliance.classList.add('active');
                btnOcean.classList.remove('active');
                currentMode = 'appliance';
                renderCurrentFrame();
                Toast.show('视角已切换', '暖阳家电变频解构模式已就绪', 'info');
            });
            btnOcean.addEventListener('click', () => {
                btnOcean.classList.add('active');
                btnAppliance.classList.remove('active');
                currentMode = 'ocean';
                renderCurrentFrame();
                Toast.show('视角已切换', '录屏同款原片深海下潜模式已就绪', 'info');
            });
        }

        let ambientTime = 0;
        let isUserScrolling = false;
        let scrollTimeout = null;

        // 60fps 阻尼插值驱动渲染循环 (常态自然微动 + 滚轮推轨深入)
        function renderHomeLoop() {
            ambientTime += 0.025;

            // 当用户静止未滚动时，赋予画面自然的生活微光起伏 (如海浪般一直在动)
            let effectiveProg = currentProgress;
            if (currentProgress < 0.15 && !isUserScrolling) {
                const wave = (Math.sin(ambientTime) + 1) * 0.5 * 0.05;
                effectiveProg = Math.max(0, currentProgress + wave);
            } else if (!isUserScrolling) {
                const subWave = Math.sin(ambientTime * 1.5) * 0.008;
                effectiveProg = Math.min(1, Math.max(0, currentProgress + subWave));
            }

            currentProgress += (targetProgress - currentProgress) * 0.16;
            
            // 渲染有效帧
            const list = framePools[currentMode];
            if (list && list.length) {
                const frameIndex = Math.min(TOTAL_FRAMES - 1, Math.max(0, Math.floor(effectiveProg * (TOTAL_FRAMES - 1))));
                const img = list[frameIndex];
                if (img && img.complete && img.naturalWidth > 0) {
                    const cW = canvas.width;
                    const cH = canvas.height;
                    const imgW = img.naturalWidth;
                    const imgH = img.naturalHeight;
                    const scale = Math.max(cW / imgW, cH / imgH);
                    const drawW = imgW * scale;
                    const drawH = imgH * scale;
                    const drawX = (cW - drawW) / 2;
                    const drawY = (cH - drawH) / 2;
                    ctx.drawImage(img, drawX, drawY, drawW, drawH);
                }
            }

            // 前景文字淡出与微位移
            const heroContent = document.getElementById('home-hero-content');
            const exploreBadge = document.getElementById('home-explore-badge');
            if (heroContent) {
                if (currentProgress < 0.55) {
                    const alpha = Math.max(0, 1 - currentProgress * 1.9);
                    heroContent.style.opacity = `${alpha}`;
                    heroContent.style.transform = `translateY(${-currentProgress * 60}px)`;
                    heroContent.style.pointerEvents = alpha < 0.15 ? 'none' : 'auto';
                } else {
                    heroContent.style.opacity = '0';
                    heroContent.style.pointerEvents = 'none';
                }
            }

            if (exploreBadge) {
                exploreBadge.style.opacity = `${Math.max(0, 1 - currentProgress * 3.5)}`;
            }

            // 现场智能巡检 HUD 优雅浮现
            const deepHud = document.getElementById('home-deep-hud');
            if (deepHud) {
                if (currentProgress >= 0.40 && currentProgress <= 0.92) {
                    const hudAlpha = Math.min(1, (currentProgress - 0.40) * 4);
                    deepHud.style.opacity = `${hudAlpha}`;
                    deepHud.style.transform = `translate(-50%, ${-(currentProgress - 0.40) * 30}px)`;
                } else {
                    deepHud.style.opacity = '0';
                }
            }

            requestAnimationFrame(renderHomeLoop);
        }

        function onHomeScroll() {
            isUserScrolling = true;
            if (scrollTimeout) clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(() => {
                isUserScrolling = false;
            }, 300);

            const rect = track.getBoundingClientRect();
            const scrollDistance = -rect.top;
            const maxScroll = track.clientHeight - window.innerHeight;
            if (maxScroll <= 0) return;

            targetProgress = Math.min(Math.max(scrollDistance / maxScroll, 0), 1);
        }

        window.addEventListener('scroll', onHomeScroll, { passive: true });
        // 初始化设置画布
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        // 首帧在首张图加载后立即绘制
        framePools.appliance[0].onload = () => {
            renderCurrentFrame();
        };
        setTimeout(renderCurrentFrame, 150);

        // ── 故障体检透视工作台 Chip 交互联动 ──
        const symptomChips = document.querySelectorAll('.wb-symptom-chip');
        const titleEl = document.getElementById('wb-appliance-title');
        const partEl = document.getElementById('wb-part-name');
        const descEl = document.getElementById('wb-symptom-desc');
        const sopEl = document.getElementById('wb-sop-desc');
        const feeEl = document.getElementById('wb-fee-display');
        const warEl = document.getElementById('wb-warranty-pill');

        if (symptomChips.length && titleEl && partEl) {
            symptomChips.forEach(chip => {
                chip.addEventListener('click', () => {
                    symptomChips.forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');

                    titleEl.textContent = `${chip.dataset.appliance} · 智能诊断透视`;
                    partEl.textContent = chip.dataset.part;
                    descEl.textContent = chip.dataset.symptom;
                    sopEl.textContent = `✓ ${chip.dataset.sop}`;
                    feeEl.textContent = chip.dataset.fee;
                    warEl.textContent = chip.dataset.warranty;

                    // 闪烁高亮提示
                    partEl.parentElement.classList.add('triaging-flash');
                    setTimeout(() => {
                        partEl.parentElement.classList.remove('triaging-flash');
                    }, 400);
                });
            });
        }

        // ── 家电明码标价分类 Tab 切换 ──
        const tabBtns = document.querySelectorAll('.appliance-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const idx = btn.getAttribute('data-cat-idx');
                document.querySelectorAll('.pricing-panel').forEach(p => p.classList.remove('active'));
                const activePanel = document.getElementById(`pricing-panel-${idx}`);
                if (activePanel) activePanel.classList.add('active');
            });
        });

        // ── 故障分类联动费用智能估算微面板 ──
        const categorySelect = document.getElementById('qb-category');
        const laborFeeDisplay = document.getElementById('calc-labor-fee');
        const totalDisplay = document.getElementById('calc-total-display');
        if (categorySelect && laborFeeDisplay && totalDisplay) {
            const laborMap = {
                '变频空调': '¥60.00 ~ ¥120.00',
                '滚筒洗衣机': '¥50.00 ~ ¥90.00',
                '风冷冰箱': '¥60.00 ~ ¥100.00',
                '吸油烟机': '¥70.00 ~ ¥110.00',
                '燃气灶': '¥45.00 ~ ¥80.00',
                '储水式电热水器': '¥55.00 ~ ¥95.00',
                '其他常用家用电器': '¥40.00 ~ ¥80.00'
            };
            categorySelect.addEventListener('change', () => {
                const val = categorySelect.value;
                const labor = laborMap[val] || '¥50.00 ~ ¥90.00';
                laborFeeDisplay.textContent = labor;
                const baseMin = labor.match(/\d+/);
                totalDisplay.textContent = baseMin ? `¥${baseMin[0]}.00 起` : '¥50.00 起';
            });
        }

        // ── 30 秒极速一键报修表单提交 ──
        const bookForm = document.getElementById('quick-book-form');
        const submitBtn = document.getElementById('qb-submit-btn');
        const resultBox = document.getElementById('qb-result-box');
        if (bookForm && submitBtn && resultBox) {
            bookForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span>⏳ 正在指派附近金牌工匠...</span>';
                resultBox.style.display = 'none';

                const payload = {
                    name: document.getElementById('qb-name').value.trim(),
                    phone: document.getElementById('qb-phone').value.trim(),
                    category: document.getElementById('qb-category').value,
                    address: document.getElementById('qb-address').value.trim(),
                    description: document.getElementById('qb-desc').value.trim()
                };

                try {
                    const res = await fetch('/api/home-repair/quick-book', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    const data = await res.json();
                    if (res.ok && data.status === 'success') {
                        resultBox.style.display = 'block';
                        resultBox.style.color = '#15803d';
                        resultBox.style.background = '#f0fdf4';
                        resultBox.style.padding = '14px 18px';
                        resultBox.style.borderRadius = '10px';
                        resultBox.style.border = '1.5px solid #bbf7d0';
                        resultBox.innerHTML = `<strong>🎉 预约成功！</strong><br>${data.message}`;
                        bookForm.reset();
                        Toast.show('预约成功', `工单号：${data.order_no}，工程师马上联系您！`, 'success');
                    } else {
                        throw new Error(data.message || '提交失败，请稍后重试');
                    }
                } catch (err) {
                    resultBox.style.display = 'block';
                    resultBox.style.color = '#b91c1c';
                    resultBox.style.background = '#fef2f2';
                    resultBox.style.padding = '14px 18px';
                    resultBox.style.borderRadius = '10px';
                    resultBox.style.border = '1.5px solid #fecaca';
                    resultBox.textContent = `❌ ${err.message}`;
                    Toast.show('预约失败', err.message, 'error');
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<span>立即提交预约 · 免费派工上门检测</span>';
                }
            });
        }
    };

    // ── 11. Viktor Oddy 极简设计系统交互体系 (口碑轮播 + 视差微调) ──
    window.initViktorOddyInteractions = function() {
        const slides = document.querySelectorAll('.vo-review-slide');
        const dots = document.querySelectorAll('.vo-review-dot');
        if (slides.length > 0 && dots.length > 0) {
            let activeIdx = 0;
            const showSlide = (idx) => {
                slides.forEach((s, i) => s.classList.toggle('active', i === idx));
                dots.forEach((d, i) => d.classList.toggle('active', i === idx));
                activeIdx = idx;
            };

            dots.forEach((dot, idx) => {
                dot.addEventListener('click', () => showSlide(idx));
            });

            // 自动每 4 秒轮换
            setInterval(() => {
                const next = (activeIdx + 1) % slides.length;
                showSlide(next);
            }, 4000);
        }

        // 视差人物图片平滑滚动
        const parallaxImg = document.getElementById('vo-parallax-hero-img');
        if (parallaxImg) {
            window.addEventListener('scroll', () => {
                const rect = parallaxImg.getBoundingClientRect();
                const vh = window.innerHeight;
                if (rect.top < vh && rect.bottom > 0) {
                    const offset = ((vh - rect.top) / (vh + rect.height) - 0.5) * 80;
                    parallaxImg.style.transform = `translateY(${offset}px)`;
                }
            }, { passive: true });
        }
    };

    // 页面初始化自启全部动效体系
    document.addEventListener('DOMContentLoaded', () => {
        window.initCopilot();
        window.initSpotlight();
        window.initTilt3D();
        window.initHeroCanvas();
        window.initCountUp();
        window.initPCBTraces();
        window.initHologramScanner();
        window.initTriagingWorkbench();
        window.initPortalCanvasScrolly();
        window.initHomeRepairPage();
        window.initViktorOddyInteractions();
    });

})();

