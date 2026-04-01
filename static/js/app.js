        const STORAGE_KEY = 'adventure_game_save';
        const SESSION_ID_KEY = 'adventure_tab_session_id';

        function getSessionId() {
            let sessionId = sessionStorage.getItem(SESSION_ID_KEY);
            if (!sessionId) {
                sessionId = Date.now().toString() + Math.random().toString(36).substr(2, 9);
                sessionStorage.setItem(SESSION_ID_KEY, sessionId);
            }
            return sessionId;
        }

        async function apiFetch(url, options) {
            const sessionId = getSessionId();
            options = options || {};
            options.headers = options.headers || {};
            options.headers['X-Adventure-Session-ID'] = sessionId;
            if (options.body && !options.headers['Content-Type']) {
                options.headers['Content-Type'] = 'application/json';
            }
            return fetch(url, options);
        }

        let messages = [];
        let chapter = 0;
        let logs = [];
        let currentScene = null;
        let currentChoices = null;
        let endingTriggered = false;
        let endingCountdown = 0;
        let worldSetting = "";
        let selectedEndingType = "";
        let playerCharacter = null;
        let selectedSkills = [];
        let presetSkills = {};
        let playerAttributes = {
            strength: 10,
            dexterity: 10,
            constitution: 10,
            intelligence: 10,
            wisdom: 10,
            charisma: 10
        };

        let routeScores = { redemption: 0, power: 0, sacrifice: 0, betrayal: 0, retreat: 0 };
        let keyDecisions = [];
        let endingOmenState = {};

        const tendencyToRouteMap = {
            "善良": "redemption",
            "正义": "redemption",
            "勇敢": "power",
            "冷酷": "power",
            "仁慈": "sacrifice",
            "理性": "sacrifice",
            "自利": "betrayal",
            "狡诈": "betrayal",
            "谨慎": "retreat",
            "坦诚": "retreat",
            "感性": "redemption"
        };

        function getRouteLeader() {
            let leader = null;
            let maxScore = 0;
            for (const [route, score] of Object.entries(routeScores)) {
                if (score > maxScore) {
                    maxScore = score;
                    leader = route;
                }
            }
            return leader;
        }

        function setChoiceButtonLabel(btn, text) {
            let label = btn.querySelector('.choice-btn-label');
            if (!label) {
                label = document.createElement('span');
                label.className = 'choice-btn-label';
                btn.appendChild(label);
            }
            label.textContent = text;
        }

        function decorateChoiceExtras(btn, choice) {
            if (!choice || typeof choice !== 'object') return;
            if (choice.is_key_decision) {
                const badge = document.createElement('span');
                badge.className = 'key-decision-badge';
                badge.textContent = '命运转折点';
                btn.insertBefore(badge, btn.firstChild);
            }
            if (choice.tendency && choice.tendency.length > 0) {
                const tagsDiv = document.createElement('div');
                tagsDiv.className = 'choice-tendency-tags';
                choice.tendency.forEach(t => {
                    const tag = document.createElement('span');
                    tag.className = 'tendency-tag';
                    tag.textContent = t;
                    tagsDiv.appendChild(tag);
                });
                btn.appendChild(tagsDiv);
            }
            const wis = playerCharacter != null
                ? (typeof playerCharacter.wisdom === 'number' ? playerCharacter.wisdom : (parseInt(playerCharacter.wisdom, 10) || 0))
                : 0;
            if (choice.consequence_hint && playerCharacter && wis >= 14) {
                const hint = document.createElement('div');
                hint.className = 'consequence-hint';
                hint.textContent = choice.consequence_hint;
                btn.appendChild(hint);
            }
        }

        async function loadPresetSkills() {
            try {
                const response = await apiFetch('/api/player/skills');
                const data = await response.json();
                presetSkills = data.skills;
                renderSkillsGrid();
            } catch (error) {
                console.error('加载预设技能失败:', error);
            }
        }

        function renderSkillsGrid() {
            const container = document.getElementById('skills-container');
            if (!container) return;
            
            container.innerHTML = '';
            
            const categoryNames = {
                combat: '⚔️ 战斗',
                social: '💬 社交',
                knowledge: '📚 知识',
                survival: '🏕️ 生存'
            };
            
            for (const [category, skills] of Object.entries(presetSkills)) {
                const categoryLabel = document.createElement('div');
                categoryLabel.className = 'skill-category-label';
                categoryLabel.textContent = categoryNames[category] || category;
                container.appendChild(categoryLabel);
                
                for (const skill of skills) {
                    const checkbox = document.createElement('input');
                    checkbox.type = 'checkbox';
                    checkbox.className = 'skill-checkbox';
                    checkbox.id = `skill-${skill.name}`;
                    checkbox.value = skill.name;
                    checkbox.onchange = () => toggleSkill(skill.name);
                    
                    const label = document.createElement('label');
                    label.className = 'skill-label';
                    label.htmlFor = `skill-${skill.name}`;
                    label.textContent = skill.name;
                    
                    container.appendChild(checkbox);
                    container.appendChild(label);
                }
            }
        }

        function toggleSkill(skillName) {
            const checkbox = document.getElementById(`skill-${skillName}`);
            if (checkbox.checked) {
                if (selectedSkills.length < 3) {
                    selectedSkills.push(skillName);
                } else {
                    checkbox.checked = false;
                    alert('最多只能选择3个技能');
                }
            } else {
                selectedSkills = selectedSkills.filter(s => s !== skillName);
            }
            updateSelectedSkillsDisplay();
            updateCharacterPreview();
        }

        function updateSelectedSkillsDisplay() {
            const container = document.getElementById('selected-skills');
            if (!container) return;
            
            container.innerHTML = selectedSkills.map(skill => 
                `<span class="selected-skill-tag">${skill}</span>`
            ).join('');
        }

        function calculateModifier(value) {
            return Math.floor((value - 10) / 2);
        }

        function updateAttribute(attrName, value) {
            playerAttributes[attrName] = parseInt(value);
            
            const displayValue = document.getElementById(`${attrName.substring(0, 3)}-value`);
            const displayMod = document.getElementById(`${attrName.substring(0, 3)}-mod`);
            
            if (displayValue) displayValue.textContent = value;
            if (displayMod) displayMod.textContent = `(${calculateModifier(parseInt(value)) >= 0 ? '+' : ''}${calculateModifier(parseInt(value))})`;
            
            updateCharacterPreview();
        }

        function updateCharacterPreview() {
            const preview = document.getElementById('character-preview');
            if (!preview) return;
            
            const name = document.getElementById('player-name')?.value || '未命名';
            const age = document.getElementById('player-age')?.value || '';
            const gender = document.getElementById('player-gender')?.value || '';
            const race = document.getElementById('player-race')?.value || '';
            const background = document.getElementById('player-background')?.value || '';
            const appearance = document.getElementById('player-appearance')?.value || '';
            
            const hp = 10 + calculateModifier(playerAttributes.constitution) * 2;
            
            let content = `【${name}】\n`;
            content += `种族: ${race || '未知'} | 年龄: ${age || '未知'} | 性别: ${gender || '未知'}\n\n`;
            content += `背景: ${background || '暂无描述'}\n\n`;
            content += `外貌: ${appearance || '暂无描述'}\n\n`;
            content += `HP: ${hp}/${hp}\n\n`;
            content += `属性:\n`;
            content += `  力量 ${playerAttributes.strength} (${calculateModifier(playerAttributes.strength) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.strength)})\n`;
            content += `  敏捷 ${playerAttributes.dexterity} (${calculateModifier(playerAttributes.dexterity) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.dexterity)})\n`;
            content += `  体质 ${playerAttributes.constitution} (${calculateModifier(playerAttributes.constitution) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.constitution)})\n`;
            content += `  智力 ${playerAttributes.intelligence} (${calculateModifier(playerAttributes.intelligence) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.intelligence)})\n`;
            content += `  感知 ${playerAttributes.wisdom} (${calculateModifier(playerAttributes.wisdom) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.wisdom)})\n`;
            content += `  魅力 ${playerAttributes.charisma} (${calculateModifier(playerAttributes.charisma) >= 0 ? '+' : ''}${calculateModifier(playerAttributes.charisma)})\n`;
            
            if (selectedSkills.length > 0) {
                content += `\n技能: ${selectedSkills.join(', ')}`;
            }
            
            preview.textContent = content;
        }

        function switchCreationTab(tab) {
            document.querySelectorAll('.creation-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.creation-content').forEach(c => c.classList.remove('active'));
            
            if (tab === 'custom') {
                document.querySelector('.creation-tab:nth-child(1)').classList.add('active');
                document.getElementById('custom-creation').classList.add('active');
            } else {
                document.querySelector('.creation-tab:nth-child(2)').classList.add('active');
                document.getElementById('random-creation').classList.add('active');
            }
        }

        async function generateRandomPlayer() {
            try {
                const response = await apiFetch('/api/player/random', {
                    method: 'POST',
                    body: JSON.stringify({ world_setting: '' })
                });

                const data = await response.json();
                if (data.success) {
                    playerCharacter = data.player;
                    displayRandomPlayer(data.player);
                }
            } catch (error) {
                console.error('随机生成角色失败:', error);
                alert('随机生成角色失败');
            }
        }

        function displayRandomPlayer(player) {
            document.getElementById('player-name').value = player.name || '';
            document.getElementById('player-age').value = player.age || '';
            document.getElementById('player-gender').value = player.gender || '';
            document.getElementById('player-race').value = player.race || '';
            document.getElementById('player-background').value = player.background || '';
            document.getElementById('player-appearance').value = player.appearance || '';
            
            playerAttributes = {
                strength: player.strength || 10,
                dexterity: player.dexterity || 10,
                constitution: player.constitution || 10,
                intelligence: player.intelligence || 10,
                wisdom: player.wisdom || 10,
                charisma: player.charisma || 10
            };
            
            ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma'].forEach(attr => {
                const slider = document.getElementById(`attr-${attr}`);
                const displayValue = document.getElementById(`${attr.substring(0, 3)}-value`);
                const displayMod = document.getElementById(`${attr.substring(0, 3)}-mod`);
                
                if (slider) slider.value = playerAttributes[attr];
                if (displayValue) displayValue.textContent = playerAttributes[attr];
                if (displayMod) displayMod.textContent = `(${calculateModifier(playerAttributes[attr]) >= 0 ? '+' : ''}${calculateModifier(playerAttributes[attr])})`;
            });
            
            selectedSkills = (player.skills || []).map(s => s.name);
            updateSelectedSkillsDisplay();
            
            document.querySelectorAll('.skill-checkbox').forEach(cb => {
                cb.checked = selectedSkills.includes(cb.value);
            });
            
            updateCharacterPreview();
        }

        async function confirmCharacterCreation() {
            const name = document.getElementById('player-name')?.value?.trim();
            if (!name) {
                alert('请输入角色名称');
                return;
            }

            if (selectedSkills.length < 2) {
                alert('请至少选择2个技能');
                return;
            }

            try {
                const response = await apiFetch('/api/player/create', {
                    method: 'POST',
                    body: JSON.stringify({
                        name: name,
                        age: parseInt(document.getElementById('player-age')?.value) || null,
                        gender: document.getElementById('player-gender')?.value || null,
                        race: document.getElementById('player-race')?.value || null,
                        background: document.getElementById('player-background')?.value || '',
                        appearance: document.getElementById('player-appearance')?.value || '',
                        strength: playerAttributes.strength,
                        dexterity: playerAttributes.dexterity,
                        constitution: playerAttributes.constitution,
                        intelligence: playerAttributes.intelligence,
                        wisdom: playerAttributes.wisdom,
                        charisma: playerAttributes.charisma,
                        skills: selectedSkills
                    })
                });

                const data = await response.json();
                if (data.success) {
                    playerCharacter = data.player;
                    showStartScreen();
                }
            } catch (error) {
                console.error('创建角色失败:', error);
                alert('创建角色失败');
            }
        }

        function skipToStartScreen() {
            playerCharacter = null;
            showStartScreen();
        }

        async function loadPlayerCharacter() {
            try {
                const response = await apiFetch('/api/player');
                const data = await response.json();
                if (data.exists) {
                    playerCharacter = data.player;
                    return true;
                }
                return false;
            } catch (error) {
                console.error('加载角色失败:', error);
                return false;
            }
        }

        function showCharacterCreationScreen() {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('character-creation-screen').classList.add('active');
            loadPresetSkills();
            updateCharacterPreview();
        }

        function showStartScreen() {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('start-screen').classList.add('active');
        }

        function showCharacterReviewScreen() {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById('character-review-screen').classList.add('active');
            loadCharacterForReview();
        }

        async function loadCharacterForReview() {
            try {
                const response = await apiFetch('/api/player');
                const data = await response.json();
                
                if (data.exists && data.player) {
                    const player = data.player;
                    
                    document.getElementById('review-name').value = player.name || '';
                    document.getElementById('review-age').value = player.age || '';
                    document.getElementById('review-gender').value = player.gender || '';
                    document.getElementById('review-race').value = player.race || '';
                    document.getElementById('review-title').value = player.title || '';
                    document.getElementById('review-appearance').value = player.appearance || '';
                    document.getElementById('review-background').value = player.background || '';
                    document.getElementById('review-personality').value = player.personality || '';
                    
                    document.getElementById('review-strength').value = player.strength || 10;
                    document.getElementById('review-dexterity').value = player.dexterity || 10;
                    document.getElementById('review-constitution').value = player.constitution || 10;
                    document.getElementById('review-intelligence').value = player.intelligence || 10;
                    document.getElementById('review-wisdom').value = player.wisdom || 10;
                    document.getElementById('review-charisma').value = player.charisma || 10;
                    
                    updateReviewPoints();
                    
                    const skillsContainer = document.getElementById('review-skills-container');
                    skillsContainer.innerHTML = '';
                    
                    if (player.skills && player.skills.length > 0) {
                        player.skills.forEach((skill, index) => {
                            const skillTag = document.createElement('div');
                            skillTag.className = 'skill-tag';
                            skillTag.innerHTML = `
                                <span class="skill-name">${skill.name}</span>
                                <span class="skill-level">Lv.${skill.level || 1}</span>
                                <button class="remove-skill" onclick="removeReviewSkill(${index})">×</button>
                            `;
                            skillsContainer.appendChild(skillTag);
                        });
                    }
                }
            } catch (error) {
                console.error('加载主角信息失败:', error);
            }
        }

        function updateReviewPoints() {
            const str = parseInt(document.getElementById('review-strength').value) || 0;
            const dex = parseInt(document.getElementById('review-dexterity').value) || 0;
            const con = parseInt(document.getElementById('review-constitution').value) || 0;
            const int = parseInt(document.getElementById('review-intelligence').value) || 0;
            const wis = parseInt(document.getElementById('review-wisdom').value) || 0;
            const cha = parseInt(document.getElementById('review-charisma').value) || 0;
            
            const total = str + dex + con + int + wis + cha;
            document.getElementById('review-points-info').textContent = `总点数: ${total}`;
        }

        function removeReviewSkill(index) {
            const skillsContainer = document.getElementById('review-skills-container');
            const skillTags = skillsContainer.querySelectorAll('.skill-tag');
            if (skillTags[index]) {
                skillTags[index].remove();
            }
        }

        async function confirmCharacterReview() {
            const name = document.getElementById('review-name').value.trim();
            if (!name) {
                alert('请输入角色名称');
                return;
            }
            
            const skills = [];
            document.querySelectorAll('#review-skills-container .skill-tag').forEach(tag => {
                const skillName = tag.querySelector('.skill-name').textContent;
                const levelText = tag.querySelector('.skill-level').textContent;
                const level = parseInt(levelText.replace('Lv.', '')) || 1;
                skills.push({ name: skillName, level: level });
            });
            
            const playerData = {
                name: name,
                age: parseInt(document.getElementById('review-age').value) || null,
                gender: document.getElementById('review-gender').value || null,
                race: document.getElementById('review-race').value || null,
                title: document.getElementById('review-title').value || '',
                appearance: document.getElementById('review-appearance').value || '',
                background: document.getElementById('review-background').value || '',
                personality: document.getElementById('review-personality').value || '',
                strength: parseInt(document.getElementById('review-strength').value) || 10,
                dexterity: parseInt(document.getElementById('review-dexterity').value) || 10,
                constitution: parseInt(document.getElementById('review-constitution').value) || 10,
                intelligence: parseInt(document.getElementById('review-intelligence').value) || 10,
                wisdom: parseInt(document.getElementById('review-wisdom').value) || 10,
                charisma: parseInt(document.getElementById('review-charisma').value) || 10,
                skills: skills
            };
            
            try {
                // 保存主角信息
                const response = await apiFetch('/api/player', {
                    method: 'PUT',
                    body: JSON.stringify(playerData)
                });
                
                const result = await response.json();
                if (result.success) {
                    playerCharacter = result.player;
                    
                    // 生成NPC角色
                    await generateNPCs();
                } else {
                    alert('保存失败: ' + (result.error || '未知错误'));
                }
            } catch (error) {
                console.error('保存主角信息失败:', error);
                alert('保存失败');
            }
        }

        async function generateNPCs() {
            // 显示NPC生成进度
            document.getElementById('loading-overlay')?.remove();
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.className = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <div id="loading-text">正在生成配角NPC，请稍候...</div>
                <div id="loading-detail" style="margin-top: 10px; font-size: 0.8rem; opacity: 0.7;">正在使用AI生成10个NPC角色...</div>
            `;
            document.body.appendChild(overlay);
            
            try {
                const npcController = new AbortController();
                const npcTimeout = setTimeout(() => npcController.abort(), 120000);
                
                const npcResponse = await apiFetch('/api/npcs/generate', {
                    method: 'POST',
                    body: JSON.stringify({
                        world_setting: worldSetting,
                        protagonist_info: playerCharacter,
                        npc_count: 10
                    }),
                    signal: npcController.signal
                });
                clearTimeout(npcTimeout);
                
                const npcData = await npcResponse.json();
                if (npcData.success) {
                    console.log('NPC生成成功:', npcData.message);
                    await loadCharactersList();
                } else {
                    console.warn('NPC生成警告:', npcData.error || '未知错误');
                }
            } catch (e) {
                console.error('NPC生成失败:', e);
                // NPC生成失败不阻断游戏流程
            } finally {
                document.getElementById('loading-overlay')?.remove();
            }
            
            // 开始游戏
            await startGameWithCharacter();
        }

        async function regenerateCharacter() {
            const worldSetting = document.getElementById('world-setting').value.trim();
            if (!worldSetting) {
                alert('请先输入故事设定');
                return;
            }
            
            try {
                // 使用LLM重新生成主角
                const response = await apiFetch('/api/player/generate', {
                    method: 'POST',
                    body: JSON.stringify({ world_setting: worldSetting })
                });
                
                const data = await response.json();
                if (data.success) {
                    playerCharacter = data.player;
                    loadCharacterForReview();
                } else {
                    alert('重新生成失败: ' + (data.error || '未知错误'));
                }
            } catch (error) {
                console.error('重新生成角色失败:', error);
                alert('重新生成失败');
            }
        }

        function togglePlayerPanel() {
            const panel = document.getElementById('player-panel');
            panel.classList.toggle('open');
            document.getElementById('character-panel').classList.remove('open');
            if (panel.classList.contains('open')) {
                updatePlayerPanel();
            }
        }

        function updatePlayerPanel() {
            const infoDiv = document.getElementById('player-info');
            if (!infoDiv || !playerCharacter) {
                infoDiv.innerHTML = '<p style="color: #888;">未创建角色</p>';
                return;
            }
            
            const hpPercent = (playerCharacter.current_hp / playerCharacter.max_hp) * 100;
            
            let content = `
                <div class="player-name">${playerCharacter.name}</div>
                <div class="player-basic-info">
                    ${playerCharacter.race || ''} ${playerCharacter.age ? playerCharacter.age + '岁' : ''} ${playerCharacter.gender || ''}
                </div>
                
                <div class="player-hp-bar">
                    <div class="hp-label">
                        <span>❤️ HP</span>
                        <span>${playerCharacter.current_hp}/${playerCharacter.max_hp}</span>
                    </div>
                    <div class="hp-bar-bg">
                        <div class="hp-bar-fill" style="width: ${hpPercent}%"></div>
                    </div>
                </div>
                
                <div class="player-attributes">
                    <h4>属性</h4>
                    <div class="player-attr-grid">
                        <div class="player-attr-item">
                            <span class="player-attr-name">力量</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.strength}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.strength) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.strength)})</span>
                            </span>
                        </div>
                        <div class="player-attr-item">
                            <span class="player-attr-name">敏捷</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.dexterity}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.dexterity) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.dexterity)})</span>
                            </span>
                        </div>
                        <div class="player-attr-item">
                            <span class="player-attr-name">体质</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.constitution}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.constitution) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.constitution)})</span>
                            </span>
                        </div>
                        <div class="player-attr-item">
                            <span class="player-attr-name">智力</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.intelligence}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.intelligence) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.intelligence)})</span>
                            </span>
                        </div>
                        <div class="player-attr-item">
                            <span class="player-attr-name">感知</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.wisdom}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.wisdom) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.wisdom)})</span>
                            </span>
                        </div>
                        <div class="player-attr-item">
                            <span class="player-attr-name">魅力</span>
                            <span>
                                <span class="player-attr-value">${playerCharacter.charisma}</span>
                                <span class="player-attr-mod">(${calculateModifier(playerCharacter.charisma) >= 0 ? '+' : ''}${calculateModifier(playerCharacter.charisma)})</span>
                            </span>
                        </div>
                    </div>
                </div>
            `;
            
            if (playerCharacter.skills && playerCharacter.skills.length > 0) {
                content += `
                    <div class="player-skills">
                        <h4>技能</h4>
                        <div class="player-skill-list">
                            ${playerCharacter.skills.map(s => `<span class="player-skill-tag">${s.name} Lv.${s.level}</span>`).join('')}
                        </div>
                    </div>
                `;
            }
            
            if (playerCharacter.background) {
                content += `
                    <div style="margin-top: 15px;">
                        <h4 style="color: #00ff88; margin-bottom: 8px;">背景</h4>
                        <p style="color: #aaffcc; font-size: 0.85rem; line-height: 1.5;">${playerCharacter.background}</p>
                    </div>
                `;
            }
            
            infoDiv.innerHTML = content;
        }

        function saveGameState() {
            try {
                const gameState = {
                    messages: messages,
                    chapter: chapter,
                    logs: logs,
                    currentScene: currentScene,
                    currentChoices: currentChoices,
                    endingTriggered: endingTriggered,
                    endingCountdown: endingCountdown,
                    worldSetting: worldSetting,
                    selectedEndingType: selectedEndingType,
                    routeScores: routeScores,
                    keyDecisions: keyDecisions,
                    endingOmenState: endingOmenState,
                    timestamp: Date.now()
                };
                localStorage.setItem(STORAGE_KEY, JSON.stringify(gameState));
                console.log('游戏状态已保存');
            } catch (e) {
                console.error('保存游戏状态失败:', e);
                if (e.name === 'QuotaExceededError') {
                    console.error('存储空间不足，无法保存游戏状态');
                }
            }
        }

        function loadGameState() {
            try {
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {
                    const gameState = JSON.parse(saved);
                    const hoursSinceSave = (Date.now() - gameState.timestamp) / (1000 * 60 * 60);
                    
                    if (hoursSinceSave > 24) {
                        console.log('存档已超过24小时，清除旧存档');
                        clearGameState();
                        return null;
                    }
                    
                    return gameState;
                }
            } catch (e) {
                console.error('加载游戏状态失败:', e);
                clearGameState();
            }
            return null;
        }

        function clearGameState() {
            try {
                localStorage.removeItem(STORAGE_KEY);
                console.log('游戏状态已清除');
            } catch (e) {
                console.error('清除游戏状态失败:', e);
            }
        }

        function restoreGameState(gameState) {
            if (!gameState) return;
            
            messages = gameState.messages || [];
            chapter = gameState.chapter || 0;
            logs = gameState.logs || [];
            currentScene = gameState.currentScene;
            currentChoices = gameState.currentChoices;
            endingTriggered = gameState.endingTriggered || false;
            endingCountdown = gameState.endingCountdown || 0;
            worldSetting = gameState.worldSetting || "";
            selectedEndingType = gameState.selectedEndingType || "";
            routeScores = gameState.routeScores || { redemption: 0, power: 0, sacrifice: 0, betrayal: 0, retreat: 0 };
            keyDecisions = gameState.keyDecisions || [];
            endingOmenState = gameState.endingOmenState || {};

            document.getElementById('chapter-num').textContent = chapter;
            
            _renderLogEntries(logs);

            if (currentScene) {
                document.getElementById('scene-text').textContent = currentScene;
            }

            if (currentChoices && currentChoices.length > 0) {
                _renderChoiceItems(currentChoices);
            }

            if (endingTriggered) {
                document.getElementById('end-game-btn').disabled = true;
                document.getElementById('end-game-btn').textContent = '收尾中...';
                document.getElementById('custom-choice-container').style.display = 'none';
            }

            console.log('游戏状态已恢复');

            const undoBtn = document.getElementById('undo-btn');
            if (undoBtn) {
                undoBtn.style.display = 'flex';
            }
            updateUndoButton();
        }

        // ── Shared rendering helpers for restore flows ──────

        function _renderLogEntries(logsList) {
            const logContainer = document.getElementById('log-container');
            logContainer.innerHTML = '';
            logsList.forEach((log, idx) => {
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                if (log && typeof log === 'object' && log.log) {
                    entry.innerHTML = `<span class="log-chapter-num">【第${idx + 1}轮】</span> ${log.log}`;
                } else if (typeof log === 'string') {
                    entry.textContent = log;
                } else {
                    entry.textContent = JSON.stringify(log);
                }
                logContainer.appendChild(entry);
            });
            logContainer.scrollTop = logContainer.scrollHeight;
        }

        function _renderChoiceItems(choices) {
            const choicesContainer = document.getElementById('choices-container');
            choicesContainer.innerHTML = '';

            choices.forEach((choice, index) => {
                // Handle both ChoiceItem objects and plain strings
                if (typeof choice === 'string') {
                    const btn = document.createElement('button');
                    btn.className = 'choice-btn';
                    setChoiceButtonLabel(btn, `${index + 1}. ${choice}`);
                    btn.onclick = () => makeChoice(choice);
                    choicesContainer.appendChild(btn);
                    return;
                }

                // ChoiceItem object with .text, .check, .tendency, etc.
                if (choice.check && choice.check_optional) {
                    const container = document.createElement('div');
                    container.className = 'choice-with-check';

                    const textDiv = document.createElement('div');
                    textDiv.className = 'choice-with-check-text';
                    textDiv.textContent = `${index + 1}. ${choice.text}`;
                    if (choice.check_prompt) {
                        const promptDiv = document.createElement('div');
                        promptDiv.className = 'choice-with-check-prompt';
                        promptDiv.textContent = choice.check_prompt;
                        textDiv.appendChild(promptDiv);
                    }
                    container.appendChild(textDiv);

                    const btnGroup = document.createElement('div');
                    btnGroup.className = 'choice-with-check-actions';

                    const directBtn = document.createElement('button');
                    directBtn.className = 'btn btn-secondary';
                    directBtn.textContent = '直接行动';
                    directBtn.onclick = () => makeChoiceWithCheck(choice.text, null, choice);
                    btnGroup.appendChild(directBtn);

                    const checkBtn = document.createElement('button');
                    checkBtn.className = 'choice-btn has-check';
                    setChoiceButtonLabel(checkBtn, '🎲 进行检定');
                    checkBtn.onclick = () => {
                        const checkData = choice.check || {};
                        performDiceCheck(
                            checkData.attribute || 'strength',
                            checkData.skill || '',
                            checkData.difficulty || 12,
                            checkData.description || ''
                        ).then(result => {
                            lastCheckResult = result;
                            if (result.success) {
                                makeChoiceWithCheck(choice.text + `（检定成功：${result.total} ≥ ${checkData.difficulty || 12}）`, result, choice);
                            } else {
                                makeChoiceWithCheck(choice.text + `（检定失败：${result.total} < ${checkData.difficulty || 12}）`, result, choice);
                            }
                        });
                    };
                    btnGroup.appendChild(checkBtn);

                    container.appendChild(btnGroup);
                    choicesContainer.appendChild(container);
                } else if (choice.check) {
                    const btn = document.createElement('button');
                    btn.className = 'choice-btn has-check';
                    setChoiceButtonLabel(btn, `${index + 1}. ${choice.text}`);
                    decorateChoiceExtras(btn, choice);
                    btn.onclick = () => {
                        const checkData = choice.check || {};
                        performDiceCheck(
                            checkData.attribute || 'strength',
                            checkData.skill || '',
                            checkData.difficulty || 12,
                            checkData.description || ''
                        ).then(result => {
                            lastCheckResult = result;
                            if (result.success) {
                                makeChoiceWithCheck(choice.text + `（检定成功：${result.total} ≥ ${checkData.difficulty || 12}）`, result, choice);
                            } else {
                                makeChoiceWithCheck(choice.text + `（检定失败：${result.total} < ${checkData.difficulty || 12}）`, result, choice);
                            }
                        });
                    };
                    choicesContainer.appendChild(btn);
                } else {
                    const btn = document.createElement('button');
                    btn.className = 'choice-btn';
                    setChoiceButtonLabel(btn, `${index + 1}. ${choice.text || choice}`);
                    decorateChoiceExtras(btn, choice);
                    btn.onclick = () => makeChoiceWithCheck(choice.text || choice, null, typeof choice === 'object' ? choice : null);
                    choicesContainer.appendChild(btn);
                }
            });
        }

        let currentCheckCallback = null;

        async function performDiceCheck(attribute, skill, difficulty, description) {
            return new Promise((resolve) => {
                const modal = document.getElementById('check-modal');
                const diceDisplay = document.getElementById('dice-display');
                const diceRoll = document.getElementById('dice-roll');
                const diceModifier = document.getElementById('dice-modifier');
                const diceTotal = document.getElementById('dice-total');
                const diceDC = document.getElementById('dice-dc');
                const resultText = document.getElementById('check-result-text');
                
                modal.classList.add('active');
                diceDisplay.textContent = '?';
                diceDisplay.className = 'dice';
                diceRoll.textContent = '-';
                diceModifier.textContent = '+0';
                diceTotal.textContent = '-';
                diceDC.textContent = difficulty;
                resultText.textContent = '';
                resultText.className = 'check-result';
                
                const closeBtn = document.getElementById('check-continue-btn');
                if (closeBtn) closeBtn.style.display = 'none';
                
                currentCheckCallback = resolve;
                
                setTimeout(async () => {
                    diceDisplay.classList.add('rolling');
                    
                    let rollInterval = setInterval(() => {
                        diceDisplay.textContent = Math.floor(Math.random() * 20) + 1;
                    }, 50);
                    
                    setTimeout(async () => {
                        clearInterval(rollInterval);
                        diceDisplay.classList.remove('rolling');

                        try {
                            const response = await apiFetch('/api/check', {
                                method: 'POST',
                                body: JSON.stringify({
                                    attribute: attribute || 'strength',
                                    skill: skill || '',
                                    difficulty: difficulty || 12,
                                    description: description || ''
                                })
                            });

                            const data = await response.json();
                            if (data.success) {
                                const result = data.result;
                                
                                diceRoll.textContent = result.roll;
                                diceModifier.textContent = (result.modifier >= 0 ? '+' : '') + result.modifier + (result.skill_bonus > 0 ? `+${result.skill_bonus}` : '');
                                diceTotal.textContent = result.total;
                                diceDisplay.textContent = result.roll;

                                if (result.critical) {
                                    diceDisplay.classList.add('critical');
                                } else if (result.fumble) {
                                    diceDisplay.classList.add('fumble');
                                }
                                
                                if (result.growth) {
                                    const growthMsg = [];
                                    if (result.growth.exp_gain) growthMsg.push(`经验+${result.growth.exp_gain}`);
                                    if (result.growth.hp_effect && result.growth.hp_effect.hp_change) {
                                        const hp_change = result.growth.hp_effect.hp_change;
                                        growthMsg.push(`HP${hp_change > 0 ? '+' : ''}${hp_change}`);
                                    }
                                    if (result.growth.leveled_up) growthMsg.push(`等级提升至Lv.${result.growth.new_level}`);
                                    
                                    if (growthMsg.length > 0) {
                                        result.narrative += ` [${growthMsg.join(", ")}]`;
                                    }
                                    
                                    loadPlayerCharacter().then(() => {
                                        if (document.getElementById('player-panel').classList.contains('open')) {
                                            updatePlayerPanel();
                                        }
                                    });
                                }

                                resultText.textContent = result.narrative;
                                resultText.className = 'check-result ' + (result.success ? 'success' : 'failure');
                                
                                const closeBtn = document.getElementById('check-continue-btn');
                                if (closeBtn) {
                                    closeBtn.style.display = 'block';
                                    closeBtn.onclick = () => {
                                        modal.classList.remove('active');
                                        closeBtn.style.display = 'none';
                                        resolve(result);
                                        currentCheckCallback = null;
                                    };
                                } else {
                                    setTimeout(() => {
                                        modal.classList.remove('active');
                                        resolve(result);
                                    }, 2000);
                                }
                            }
                        } catch (error) {
                            console.error('检定请求失败:', error);
                            modal.classList.remove('active');
                            resolve({ success: false, roll: 0 });
                        }
                    }, 1500);
                }, 500);
            });
        }

        function closeCheckModal() {
            const modal = document.getElementById('check-modal');
            modal.classList.remove('active');
            if (currentCheckCallback) {
                currentCheckCallback({ success: false, roll: 0 });
                currentCheckCallback = null;
            }
        }

        function makeChoiceWithCheck(choiceText, checkInfo, choiceObj = null) {
            if (checkInfo && checkInfo.attribute) {
                const checkData = checkInfo || {};
                performDiceCheck(
                    checkData.attribute || 'strength',
                    checkData.skill || '',
                    checkData.difficulty || 12,
                    checkData.description || ''
                ).then(result => {
                    if (result.success) {
                        makeChoice(choiceText + '（检定成功）', choiceObj);
                    } else {
                        makeChoice(choiceText + '（检定失败）', choiceObj);
                    }
                });
            } else {
                makeChoice(choiceText, choiceObj);
            }
        }

        function renderChoices(choices, checks) {
            const choicesContainer = document.getElementById('choices-container');
            choicesContainer.innerHTML = '';
            
            choices.forEach((choice, index) => {
                const btn = document.createElement('button');
                btn.className = 'choice-btn';
                if (checks && checks[index]) {
                    btn.className += ' has-check';
                }
                setChoiceButtonLabel(btn, `${index + 1}. ${choice}`);
                btn.onclick = () => makeChoiceWithCheck(choice, checks ? checks[index] : null);
                choicesContainer.appendChild(btn);
            });
        }

        async function getPlayerCheckInfo() {
            try {
                const response = await apiFetch('/api/check/info');
                const data = await response.json();
                return data.info || {};
            } catch (error) {
                console.error('获取玩家检定信息失败:', error);
                return {};
            }
        }

        function showScreen(screenId) {
            document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
            document.getElementById(screenId).classList.add('active');
        }

        function showError(title, message) {
            const sceneText = document.getElementById('scene-text');
            const resultContainer = document.getElementById('novel-result');
            
            const errorHtml = `
                <div class="error-message" style="text-align: left;">
                    <div style="font-weight: bold; margin-bottom: 10px;">${title}</div>
                    <div style="font-size: 0.9rem; opacity: 0.9;">${message}</div>
                </div>
            `;
            
            if (sceneText && document.getElementById('game-screen').classList.contains('active')) {
                sceneText.innerHTML = errorHtml;
            } else if (resultContainer) {
                resultContainer.innerHTML = errorHtml;
            }
        }

        function setLoading(isLoading) {
            const loading = document.getElementById('loading');
            const choices = document.querySelectorAll('.choice-btn');
            
            if (isLoading) {
                loading.classList.add('active');
                choices.forEach(btn => btn.disabled = true);
            } else {
                loading.classList.remove('active');
                choices.forEach(btn => btn.disabled = false);
            }
        }

        function updateLog(logText) {
            logs.push(logText);
            const container = document.getElementById('log-container');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = logText;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }

        function addChapterLog(scene, choices, selectedChoice, log) {
            const chapterLog = {
                scene: scene,
                choices: choices,
                selectedChoice: selectedChoice,
                log: log
            };
            logs.push(chapterLog);
            
            const container = document.getElementById('log-container');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = log;
            container.appendChild(entry);
            container.scrollTop = container.scrollHeight;
        }

        async function expandStorySetting() {
            const userInput = document.getElementById('world-setting').value.trim();
            if (!userInput) {
                showError('请先输入故事设定', '请在上方文本框中输入简短的故事设定，AI将为你扩展成完整的世界观。');
                return;
            }

            const expandBtn = document.getElementById('expand-btn');
            const expandBtnText = document.getElementById('expand-btn-text');
            const expandLoading = document.getElementById('expand-loading');
            const expandedSetting = document.getElementById('expanded-setting');

            expandBtn.disabled = true;
            expandBtnText.style.display = 'none';
            expandLoading.style.display = 'inline';

            try {
                const controller = new AbortController();
                const timeout = setTimeout(() => controller.abort(), 120000);

                const response = await apiFetch('/api/story/expand', {
                    method: 'POST',
                    body: JSON.stringify({ user_input: userInput }),
                    signal: controller.signal
                });
                clearTimeout(timeout);

                const data = await response.json();

                if (data.success) {
                    expandedSetting.value = data.expanded_story;
                    expandedSetting.style.borderColor = '#00ff88';
                    setTimeout(() => {
                        expandedSetting.style.borderColor = '';
                    }, 2000);
                } else {
                    showError('拓展失败', data.error || '未知错误，请重试');
                }
            } catch (error) {
                if (error.name === 'AbortError') {
                    showError('请求超时', 'AI拓展请求超时，请检查网络后重试');
                } else {
                    showError('拓展失败', '网络错误，请检查连接后重试');
                }
            } finally {
                expandBtn.disabled = false;
                expandBtnText.style.display = 'inline';
                expandLoading.style.display = 'none';
            }
        }

        async function startGame() {
            const expandedSettingEl = document.getElementById('expanded-setting');
            const simpleSetting = document.getElementById('world-setting').value.trim();
            
            if (expandedSettingEl.value.trim()) {
                worldSetting = expandedSettingEl.value.trim();
            } else if (simpleSetting) {
                worldSetting = simpleSetting;
            } else {
                showError('请输入故事设定', '请在文本框中输入你想要探索的故事设定，或点击「背景拓展」生成详细设定。');
                return;
            }

            document.getElementById('loading-overlay')?.remove();
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.innerHTML = `
                <div class="loading-spinner"></div>
                <div id="loading-text">正在生成主角，请稍候...</div>
                <div id="loading-detail" style="margin-top: 10px; font-size: 0.8rem; opacity: 0.7;">正在连接AI服务...</div>
            `;
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.9);color:#00ff88;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9999;font-family:monospace;';
            document.body.appendChild(overlay);

            let errorMessage = '';

            try {
                // 步骤0: 创建新游戏
                document.getElementById('loading-detail').textContent = '正在创建新游戏...';
                const createGameResponse = await apiFetch('/api/games/create', {
                    method: 'POST',
                    body: JSON.stringify({ world_setting: worldSetting })
                });
                if (!createGameResponse.ok) {
                    throw new Error('创建游戏失败');
                }
                const createGameData = await createGameResponse.json();
                console.log('新游戏已创建:', createGameData.game_id);

                // 步骤1: 保存故事设定
                document.getElementById('loading-detail').textContent = '正在保存故事设定...';
                const memoryResponse = await apiFetch('/api/save-memory', {
                    method: 'POST',
                    body: JSON.stringify({ worldSetting: worldSetting })
                });
                if (!memoryResponse.ok) {
                    throw new Error('保存故事设定失败');
                }

                // 步骤2: 生成主角（使用LLM）
                document.getElementById('loading-detail').textContent = '正在使用AI生成主角（约需1-2分钟）...';

                const playerResponse = await apiFetch('/api/player');
                const playerData = await playerResponse.json();

                if (!playerData.exists) {
                    const playerController = new AbortController();
                    const playerTimeout = setTimeout(() => playerController.abort(), 120000);

                    const playerGenResponse = await apiFetch('/api/player/generate', {
                        method: 'POST',
                        body: JSON.stringify({ world_setting: worldSetting }),
                        signal: playerController.signal
                    });
                    clearTimeout(playerTimeout);
                    
                    const playerGenData = await playerGenResponse.json();

                    if (playerGenData.success) {
                        playerCharacter = playerGenData.player;
                        if (playerGenData.warning) {
                            console.warn('主角生成警告:', playerGenData.warning);
                        }
                    } else {
                        throw new Error('生成主角失败: ' + (playerGenData.error || '未知错误'));
                    }
                } else {
                    playerCharacter = playerData.player;
                }
                
                document.getElementById('loading-detail').textContent = '主角生成完成！';
                await new Promise(resolve => setTimeout(resolve, 500));
                
            } catch (e) {
                console.error('主角生成过程出错:', e);
                errorMessage = e.message || '主角生成过程中发生错误';
                
                if (!playerCharacter) {
                    playerCharacter = {
                        name: '冒险者',
                        age: 20,
                        gender: '其他',
                        race: '人类',
                        title: '',
                        background: '一位神秘的冒险者',
                        appearance: '看起来充满决心',
                        personality: '勇敢、好奇',
                        strength: 10,
                        dexterity: 10,
                        constitution: 10,
                        intelligence: 10,
                        wisdom: 10,
                        charisma: 10,
                        skills: []
                    };
                }
            } finally {
                document.getElementById('loading-overlay')?.remove();
            }

            if (errorMessage) {
                showError('主角生成警告', errorMessage + '\n\n将使用默认角色，你可以在编辑页面修改。');
            }

            // 显示主角编辑页面
            showCharacterReviewScreen();
        }

        async function startGameWithCharacter() {
            messages = [];
            chapter = 1;
            logs = [];
            currentScene = null;
            currentChoices = null;
            endingTriggered = false;
            endingCountdown = 0;
            document.getElementById('chapter-num').textContent = chapter;
            document.getElementById('log-container').innerHTML = '';
            document.getElementById('custom-choice-container').style.display = 'flex';
            
            await apiFetch('/api/history', { method: 'DELETE' }).catch(() => {});

            const undoBtn = document.getElementById('undo-btn');
            if (undoBtn) {
                undoBtn.style.display = 'flex';
            }
            updateUndoButton();

            document.getElementById('loading-overlay')?.remove();
            const overlay = document.createElement('div');
            overlay.id = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div><div>正在初始化游戏，请稍候...</div>';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);color:#00ff88;display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:9999;font-family:monospace;';
            document.body.appendChild(overlay);

            try {
                await loadCharactersList();
            } catch (e) {
                console.error('加载角色列表出错:', e);
            } finally {
                document.getElementById('loading-overlay')?.remove();
            }

            messages.push({
                role: 'user',
                content: `开始游戏。世界观设定：${worldSetting}`
            });

            saveGameState();
            showScreen('game-screen');
            await sendMessage();
        }

        async function makeChoice(choiceText, choiceObj = null) {
            if (choiceObj) {
                if (choiceObj.tendency) {
                    let points = choiceObj.is_key_decision ? 3 : 1;
                    choiceObj.tendency.forEach(t => {
                        const route = tendencyToRouteMap[t];
                        if (route) {
                            routeScores[route] += points;
                        }
                    });
                }
                if (choiceObj.is_key_decision) {
                    keyDecisions.push(choiceText);
                }
            }

            if (logs.length > 0) {
                logs[logs.length - 1].selectedChoice = choiceText;
            }
            
            pushHistory({
                messages: JSON.parse(JSON.stringify(messages)),
                chapter: chapter,
                current_scene: currentScene,
                current_choices: currentChoices ? JSON.parse(JSON.stringify(currentChoices)) : null,
                player: playerCharacter ? JSON.parse(JSON.stringify(playerCharacter)) : null,
                route_scores: JSON.parse(JSON.stringify(routeScores)),
                key_decisions: JSON.parse(JSON.stringify(keyDecisions)),
                ending_omen_state: JSON.parse(JSON.stringify(endingOmenState)),
                logs: JSON.parse(JSON.stringify(logs))
            });
            
            if (logs.length > 0) {
                apiFetch('/api/update-memory', {
                    method: 'POST',
                    body: JSON.stringify({
                        scene: logs[logs.length - 1].scene,
                        selectedChoice: choiceText,
                        logSummary: logs[logs.length - 1].log,
                        endingType: ''
                    })
                }).catch(e => console.error('更新memory失败:', e));
            }
            
            chapter++;
            document.getElementById('chapter-num').textContent = chapter;
            
            messages.push({
                role: 'user',
                content: choiceText
            });

            saveGameState();
            await sendMessage();
        }

        async function sendMessage() {
            setLoading(true);
            document.getElementById('scene-text').innerHTML = '';
            document.getElementById('choices-container').innerHTML = '';

            let extraPrompt = '';
            if (endingTriggered && endingCountdown > 0) {
                endingCountdown--;
                if (endingCountdown === 0) {
                    extraPrompt = `（系统提示：请生成${selectedEndingType}，必须返回ending字段，ending字段值必须与用户选择的结局类型一致）`;
                } else {
                    extraPrompt = `（系统提示：请在${endingCountdown + 1}轮内收尾并生成${selectedEndingType}）`;
                }
            }

            try {
                const response = await apiFetch('/api/chat', {
                    method: 'POST',
                    body: JSON.stringify({
                        messages: messages,
                        extraPrompt: extraPrompt,
                        turn_context: {
                            last_check: lastCheckResult,
                            route_scores: routeScores,
                            route_leader: getRouteLeader()
                        }
                    })
                });

                const data = await response.json();

                if (!data.success) {
                    throw new Error(data.error || '服务器返回错误');
                }

                const content = data.content;
                if (!content) {
                    throw new Error('API返回内容为空');
                }

                messages.push({
                    role: 'assistant',
                    content: JSON.stringify(content)
                });

                renderScene(content);

            } catch (error) {
                let errorMessage = error.message;
                let errorDetail = '';

                if (errorMessage.includes('504')) {
                    errorDetail = '服务器响应超时，请稍后重试。如果问题持续，请检查网络连接。';
                } else if (errorMessage.includes('502') || errorMessage.includes('网络请求错误')) {
                    errorDetail = '网络连接失败，请检查您的网络设置后重试。';
                } else if (errorMessage.includes('API请求失败')) {
                    errorDetail = 'AI服务暂时不可用，请稍后重试。';
                } else if (errorMessage.includes('AI返回格式错误')) {
                    errorDetail = 'AI返回的数据格式不正确，系统已自动重试。如果问题持续，请联系开发者。';
                } else if (errorMessage.includes('无法解析任何有效字段')) {
                    errorDetail = 'AI返回的内容不完整，请重试。';
                } else {
                    errorDetail = '发生了未知错误，请刷新页面重试。如果问题持续，请联系开发者。';
                }

                showError('发生错误', errorDetail);
                setLoading(false);
            }
        }

        let lastCheckResult = null;

        function renderScene(data) {
            const sceneText = document.getElementById('scene-text');
            const choicesContainer = document.getElementById('choices-container');

            sceneText.textContent = data.scene;
            currentScene = data.scene;
            currentChoices = data.choices || null;

            if (data.log) {
                logs.push({
                    scene: data.scene,
                    choices: data.choices || null,
                    selectedChoice: null,
                    log: data.log
                });

                const container = document.getElementById('log-container');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.innerHTML = `<span class="log-chapter-num">【第${chapter}轮】</span> ${data.log}`;
                container.appendChild(entry);
                container.scrollTop = container.scrollHeight;
            }

            if (data.ending_omen) {
                const container = document.getElementById('log-container');
                const omenEntry = document.createElement('div');
                omenEntry.className = 'log-entry log-entry--omen';
                omenEntry.innerHTML = `🌟 命运前兆: ${data.ending_omen}`;
                container.appendChild(omenEntry);
                container.scrollTop = container.scrollHeight;
                
                logs.push({
                    scene: '',
                    choices: null,
                    selectedChoice: null,
                    log: `🌟 命运前兆: ${data.ending_omen}`
                });
            }

            if (data.route_hint) {
                const container = document.getElementById('log-container');
                const hintEntry = document.createElement('div');
                hintEntry.className = 'log-entry log-entry--route-hint';
                hintEntry.innerHTML = `🧭 路线关注: ${data.route_hint}`;
                container.appendChild(hintEntry);
                container.scrollTop = container.scrollHeight;
                
                logs.push({
                    scene: '',
                    choices: null,
                    selectedChoice: null,
                    log: `🧭 路线关注: ${data.route_hint}`
                });
            }

            if (data.relationship_changes && data.relationship_changes.length > 0) {
                const container = document.getElementById('log-container');
                data.relationship_changes.forEach(rc => {
                    const entry = document.createElement('div');
                    entry.className = 'log-entry log-entry--relation';
                    const reason = rc.reason ? `（${rc.reason}）` : '';
                    entry.textContent = `与「${rc.character_name}」的关系 ${rc.change_type}${rc.value}${reason}`;
                    container.appendChild(entry);
                });
                container.scrollTop = container.scrollHeight;
            }

            saveGameState();

            if (data.ending) {
                setTimeout(() => {
                    showEnding(data);
                }, 2000);
                setLoading(false);
                return;
            }

            if (playerCharacter && playerCharacter.current_hp <= 0) {
                setTimeout(() => {
                    showEnding({
                        scene: data.scene + '\n\n' + (playerCharacter.name || '主角') + '的生命值已耗尽，冒险至此无奈落幕……',
                        ending: '坏结局',
                        log: '冒险终章（HP归零）'
                    });
                }, 2000);
                setLoading(false);
                return;
            }

            if (data.choices && data.choices.length > 0) {
                data.choices.forEach((choice, index) => {
                    if (choice.check && choice.check_optional) {
                        const container = document.createElement('div');
                        container.className = 'choice-with-check';

                        const textDiv = document.createElement('div');
                        textDiv.className = 'choice-with-check-text';
                        textDiv.textContent = `${index + 1}. ${choice.text}`;
                        if (choice.check_prompt) {
                            const promptDiv = document.createElement('div');
                            promptDiv.className = 'choice-with-check-prompt';
                            promptDiv.textContent = choice.check_prompt;
                            textDiv.appendChild(promptDiv);
                        }
                        container.appendChild(textDiv);

                        const btnGroup = document.createElement('div');
                        btnGroup.className = 'choice-with-check-actions';

                        const directBtn = document.createElement('button');
                        directBtn.className = 'btn btn-secondary';
                        directBtn.textContent = '直接行动';
                        directBtn.onclick = () => makeChoiceWithCheck(choice.text, null, choice);
                        btnGroup.appendChild(directBtn);

                        const checkBtn = document.createElement('button');
                        checkBtn.className = 'choice-btn has-check';
                        setChoiceButtonLabel(checkBtn, '🎲 进行检定');
                        checkBtn.onclick = () => {
                            const checkData = choice.check || {};
                            performDiceCheck(
                                checkData.attribute || 'strength',
                                checkData.skill || '',
                                checkData.difficulty || 12,
                                checkData.description || ''
                            ).then(result => {
                                lastCheckResult = result;
                                if (result.success) {
                                    makeChoiceWithCheck(choice.text + `（检定成功：${result.total} ≥ ${checkData.difficulty || 12}）`, result, choice);
                                } else {
                                    makeChoiceWithCheck(choice.text + `（检定失败：${result.total} < ${checkData.difficulty || 12}）`, result, choice);
                                }
                            });
                        };
                        btnGroup.appendChild(checkBtn);

                        container.appendChild(btnGroup);
                        choicesContainer.appendChild(container);
                    } else if (choice.check) {
                        const btn = document.createElement('button');
                        btn.className = 'choice-btn has-check';
                        setChoiceButtonLabel(btn, `${index + 1}. ${choice.text}`);
                        decorateChoiceExtras(btn, choice);
                        btn.onclick = () => {
                            const checkData = choice.check || {};
                            performDiceCheck(
                                checkData.attribute || 'strength',
                                checkData.skill || '',
                                checkData.difficulty || 12,
                                checkData.description || ''
                            ).then(result => {
                                lastCheckResult = result;
                                if (result.success) {
                                    makeChoiceWithCheck(choice.text + `（检定成功：${result.total} ≥ ${checkData.difficulty || 12}）`, result, choice);
                                } else {
                                    makeChoiceWithCheck(choice.text + `（检定失败：${result.total} < ${checkData.difficulty || 12}）`, result, choice);
                                }
                            });
                        };
                        choicesContainer.appendChild(btn);
                    } else {
                        const btn = document.createElement('button');
                        btn.className = 'choice-btn';
                        setChoiceButtonLabel(btn, `${index + 1}. ${choice.text}`);
                        decorateChoiceExtras(btn, choice);
                        btn.onclick = () => makeChoiceWithCheck(choice.text, null, choice);
                        choicesContainer.appendChild(btn);
                    }
                });
            }

            setLoading(false);
        }

        function showEnding(data) {
            const endingType = document.getElementById('ending-type');
            const endingScene = document.getElementById('ending-scene');

            if (data.scene) {
                logs.push({
                    scene: data.scene,
                    choices: null,
                    selectedChoice: null,
                    log: `【终章】${data.ending}`,
                    ending: data.ending
                });
                
                const container = document.getElementById('log-container');
                const entry = document.createElement('div');
                entry.className = 'log-entry';
                entry.textContent = `【终章】${data.ending}`;
                container.appendChild(entry);
                container.scrollTop = container.scrollHeight;

                apiFetch('/api/update-memory', {
                    method: 'POST',
                    body: JSON.stringify({
                        scene: data.scene,
                        selectedChoice: '',
                        logSummary: `【终章】${data.ending}`,
                        endingType: data.ending
                    })
                }).catch(e => console.error('更新memory失败:', e));
            }

            const generateBtn = document.getElementById('generate-novel-btn');
            generateBtn.disabled = false;
            generateBtn.style.display = 'inline-block';
            document.getElementById('novel-result').innerHTML = '';

            let typeClass = 'neutral';
            let typeText = '中立结局';
            
            if (data.ending.includes('好')) {
                typeClass = 'good';
                typeText = '好结局';
            } else if (data.ending.includes('坏')) {
                typeClass = 'bad';
                typeText = '坏结局';
            }

            endingType.className = `ending-type ${typeClass}`;
            endingType.textContent = typeText;
            endingScene.textContent = data.scene;

            showScreen('ending-screen');
        }

        function resetGame() {
            messages = [];
            chapter = 0;
            logs = [];
            currentScene = null;
            currentChoices = null;
            endingTriggered = false;
            endingCountdown = 0;
            selectedEndingType = "";
            routeScores = { redemption: 0, power: 0, sacrifice: 0, betrayal: 0, retreat: 0 };
            keyDecisions = [];
            endingOmenState = {};
            document.getElementById('world-setting').value = '';
            document.getElementById('scene-text').textContent = '';
            document.getElementById('choices-container').innerHTML = '';
            document.getElementById('log-container').innerHTML = '';
            document.getElementById('novel-result').innerHTML = '';
            document.getElementById('generate-novel-btn').style.display = 'inline-block';
            document.getElementById('ending-select-container').style.display = 'none';
            document.getElementById('custom-choice-container').style.display = 'flex';
            const endBtn = document.getElementById('end-game-btn');
            endBtn.disabled = false;
            endBtn.textContent = '结束游戏';
            clearGameState();
            const undoBtn = document.getElementById('undo-btn');
            if (undoBtn) {
                undoBtn.style.display = 'none';
            }
            showScreen('start-screen');
        }

        function triggerEnding() {
            document.getElementById('ending-select-container').style.display = 'flex';
        }

        function confirmEnding() {
            const select = document.getElementById('ending-type-select');
            selectedEndingType = select.value;
            document.getElementById('ending-select-container').style.display = 'none';
            
            endingTriggered = true;
            endingCountdown = 1;
            document.getElementById('end-game-btn').disabled = true;
            document.getElementById('end-game-btn').textContent = '收尾中...';
            document.getElementById('custom-choice-container').style.display = 'none';
            
            messages.push({
                role: 'user',
                content: `请生成${selectedEndingType}。`
            });
            
            sendMessage();
        }

        function cancelEnding() {
            document.getElementById('ending-select-container').style.display = 'none';
        }

        function submitCustomChoice() {
            const input = document.getElementById('custom-choice-input');
            const choice = input.value.trim();
            if (!choice) {
                showError('输入为空', '请在文本框中输入你想要执行的自定义选项。');
                return;
            }
            
            if (logs.length > 0 && typeof logs[logs.length - 1] === 'object') {
                logs[logs.length - 1].selectedChoice = choice;
            }
            
            input.value = '';
            makeChoice(choice);
        }

        document.getElementById('custom-choice-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitCustomChoice();
            }
        });

        // ── Novel Modal (incremental generation) ──────────────

        async function showNovelModal() {
            const modal = document.getElementById('novel-modal');
            const statusDiv = document.getElementById('novel-modal-status');
            const progressDiv = document.getElementById('novel-modal-progress');
            const resultDiv = document.getElementById('novel-modal-result');
            const generateBtn = document.getElementById('novel-modal-generate-btn');

            modal.style.display = 'flex';
            progressDiv.style.display = 'none';
            resultDiv.style.display = 'none';
            generateBtn.disabled = false;
            generateBtn.style.display = 'inline-block';
            statusDiv.textContent = '加载中...';

            try {
                const resp = await apiFetch(`/api/novel/progress?current_round=${chapter}`);
                const data = await resp.json();

                if (data.has_novel) {
                    statusDiv.innerHTML = `
                        <div style="margin-bottom:8px;"><strong>📖 《${data.title}》</strong></div>
                        <div>已有 <span style="color:#00ff88;">${data.chapters_count}</span> 章，覆盖到第 <span style="color:#00ff88;">${data.last_covered_round}</span> 轮</div>
                        <div>当前游戏已进行 <span style="color:#ffaa00;">${data.current_round}</span> 轮</div>
                        ${data.can_continue
                            ? `<div style="color:#ffaa00;margin-top:8px;">📝 有 <strong>${data.new_rounds}</strong> 轮新剧情待续写</div>`
                            : `<div style="color:#888;margin-top:8px;">✅ 小说已覆盖全部已有剧情</div>`
                        }
                    `;
                    generateBtn.textContent = data.can_continue ? '📝 续写小说' : '📖 查看小说';

                    // If nothing to continue and novel exists, show read button
                    if (!data.can_continue) {
                        generateBtn.onclick = async () => {
                            const contentResp = await apiFetch('/api/novel/content');
                            const contentData = await contentResp.json();
                            if (contentData.has_novel) {
                                resultDiv.style.display = 'block';
                                resultDiv.innerHTML = contentData.content.replace(/\n/g, '<br>');
                            }
                        };
                    } else {
                        generateBtn.onclick = () => generateNovelIncremental();
                    }
                } else {
                    if (data.current_round > 0) {
                        statusDiv.innerHTML = `
                            <div>当前游戏已进行 <span style="color:#ffaa00;">${data.current_round}</span> 轮</div>
                            <div style="color:#aaffcc;margin-top:8px;">📝 点击下方按钮为已有剧情生成小说</div>
                        `;
                        generateBtn.textContent = '📝 生成小说';
                        generateBtn.onclick = () => generateNovelIncremental();
                    } else {
                        statusDiv.innerHTML = '<div style="color:#888;">还没有游戏记录，请先开始游戏。</div>';
                        generateBtn.disabled = true;
                    }
                }
            } catch (e) {
                statusDiv.textContent = '获取进度失败: ' + e.message;
            }
        }

        function closeNovelModal() {
            document.getElementById('novel-modal').style.display = 'none';
        }

        async function generateNovelIncremental(endingType = '') {
            const statusDiv = document.getElementById('novel-modal-status');
            const progressDiv = document.getElementById('novel-modal-progress');
            const progressFill = document.getElementById('novel-modal-progress-fill');
            const progressPercent = document.getElementById('novel-modal-progress-percent');
            const progressStatus = document.getElementById('novel-modal-progress-status');
            const progressTime = document.getElementById('novel-modal-progress-time');
            const resultDiv = document.getElementById('novel-modal-result');
            const generateBtn = document.getElementById('novel-modal-generate-btn');

            generateBtn.disabled = true;
            generateBtn.style.display = 'none';
            statusDiv.textContent = '正在生成小说，请勿关闭此窗口...';
            progressDiv.style.display = 'block';
            resultDiv.style.display = 'none';

            // Fake progress animation
            progressFill.style.width = '10%';
            progressPercent.textContent = '10%';
            progressStatus.textContent = '正在规划章节结构...';
            progressTime.textContent = '这可能需要几分钟';

            let fakeProgress = 10;
            const fakeInterval = setInterval(() => {
                if (fakeProgress < 85) {
                    fakeProgress += Math.random() * 5;
                    progressFill.style.width = `${Math.round(fakeProgress)}%`;
                    progressPercent.textContent = `${Math.round(fakeProgress)}%`;
                    if (fakeProgress > 30) progressStatus.textContent = '正在生成章节内容...';
                    if (fakeProgress > 60) progressStatus.textContent = '正在合并章节...';
                }
            }, 3000);

            try {
                const resp = await apiFetch('/api/novel/incremental', {
                    method: 'POST',
                    body: JSON.stringify({ ending_type: endingType, current_round: chapter })
                });
                const data = await resp.json();
                clearInterval(fakeInterval);

                if (data.error) {
                    throw new Error(data.error);
                }

                progressFill.style.width = '100%';
                progressPercent.textContent = '100%';

                if (data.mode === 'no_change') {
                    progressStatus.textContent = '没有新内容需要续写';
                    statusDiv.textContent = data.message;
                } else {
                    const modeText = data.mode === 'fresh' ? '全新生成' : '续写';
                    progressStatus.textContent = `${modeText}完成！共 ${data.total_chapters} 章`;
                    statusDiv.innerHTML = `<div style="color:#00ff88;">✅ 小说《${data.title}》${modeText}完成，共 ${data.total_chapters} 章</div>`;
                }

                if (data.novel_content) {
                    resultDiv.style.display = 'block';
                    resultDiv.innerHTML = data.novel_content.replace(/\n/g, '<br>');
                }

                generateBtn.disabled = false;
                generateBtn.style.display = 'inline-block';
                generateBtn.textContent = '📖 刷新/续写';
                generateBtn.onclick = () => generateNovelIncremental();

            } catch (error) {
                clearInterval(fakeInterval);
                progressStatus.textContent = '生成失败';
                statusDiv.innerHTML = `<div style="color:#ff4444;">❌ ${error.message}</div>`;
                generateBtn.disabled = false;
                generateBtn.style.display = 'inline-block';
                generateBtn.textContent = '🔄 重试';
                generateBtn.onclick = () => generateNovelIncremental(endingType);
            }
        }

        // ── Ending-screen novel generation (uses incremental with ending_type) ──

        async function generateNovel() {
            // Determine ending type from the ending screen
            const endingTypeEl = document.getElementById('ending-type');
            const endingType = endingTypeEl ? endingTypeEl.textContent : '';

            const loading = document.getElementById('novel-loading');
            const resultContainer = document.getElementById('novel-result');
            const generateBtn = document.getElementById('generate-novel-btn');

            loading.classList.add('active');
            resultContainer.innerHTML = '';
            generateBtn.disabled = true;

            const progressContainer = document.createElement('div');
            progressContainer.className = 'progress-container';
            progressContainer.innerHTML = `
                <div class="progress-header">
                    <span class="progress-title">正在生成小说...</span>
                    <span class="progress-percent">0%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
                <div class="progress-info">
                    <span class="progress-status">分析游戏记忆...</span>
                    <span class="progress-time">这可能需要几分钟</span>
                </div>
            `;
            resultContainer.appendChild(progressContainer);

            const progressFill = progressContainer.querySelector('.progress-fill');
            const progressPercent = progressContainer.querySelector('.progress-percent');
            const progressStatus = progressContainer.querySelector('.progress-status');
            const progressTitle = progressContainer.querySelector('.progress-title');

            let fakeProgress = 10;
            const fakeInterval = setInterval(() => {
                if (fakeProgress < 85) {
                    fakeProgress += Math.random() * 5;
                    progressFill.style.width = `${Math.round(fakeProgress)}%`;
                    progressPercent.textContent = `${Math.round(fakeProgress)}%`;
                    if (fakeProgress > 30) progressStatus.textContent = '正在生成章节...';
                    if (fakeProgress > 60) progressStatus.textContent = '正在合并章节...';
                }
            }, 3000);

            try {
                const resp = await apiFetch('/api/novel/incremental', {
                    method: 'POST',
                    body: JSON.stringify({ ending_type: endingType, current_round: chapter })
                });
                const data = await resp.json();
                clearInterval(fakeInterval);

                if (data.error) {
                    throw new Error(data.error);
                }

                progressFill.style.width = '100%';
                progressPercent.textContent = '100%';
                progressStatus.textContent = '生成完成！';
                progressTitle.textContent = `《${data.title}》`;

                setTimeout(() => {
                    resultContainer.innerHTML = `
                        <div class="novel-content">
                            <h3>《${data.title}》生成完成</h3>
                            <p>共 ${data.total_chapters} 章</p>
                            <div class="novel-text">${data.novel_content.replace(/\n/g, '<br>')}</div>
                        </div>
                    `;
                    generateBtn.style.display = 'none';
                }, 500);

            } catch (error) {
                clearInterval(fakeInterval);
                let errorDetail = error.message.includes('memory.md不存在')
                    ? '游戏记忆文档不存在，请先开始一局游戏。'
                    : '生成失败: ' + error.message;
                showError('小说生成失败', errorDetail);
                generateBtn.disabled = false;
            } finally {
                loading.classList.remove('active');
            }
        }

        function continueGame() {
            const gameState = loadGameState();
            if (!gameState) {
                showError('无法加载存档', '没有找到有效的游戏存档，请开始新游戏。');
                return;
            }
            
            restoreGameState(gameState);
            showScreen('game-screen');
        }

        window.addEventListener('DOMContentLoaded', function() {
            const gameState = loadGameState();
            if (gameState) {
                const continueBtn = document.getElementById('continue-btn');
                if (continueBtn) {
                    continueBtn.style.display = 'inline-block';
                    console.log('检测到存档，显示继续游戏按钮');
                }
            }
            loadCharactersList();
        });

        let charactersData = [];
        let relationsData = [];
        let relationTypes = {};
        let currentCharacterId = null;

        async function loadCharactersList() {
            try {
                const response = await apiFetch('/api/characters');
                const data = await response.json();
                charactersData = data.characters || [];
                
                const relResponse = await apiFetch('/api/relations');
                const relData = await relResponse.json();
                relationsData = relData.relations || [];
                
                const typesResponse = await apiFetch('/api/relation-types');
                const typesData = await typesResponse.json();
                relationTypes = typesData.types || {};
                
                renderCharacterList();
                renderGraphLegend();
            } catch (e) {
                console.error('加载角色数据失败:', e);
            }
        }

        function toggleCharacterPanel() {
            const panel = document.getElementById('character-panel');
            panel.classList.toggle('open');
            document.getElementById('player-panel').classList.remove('open');
            if (panel.classList.contains('open')) {
                loadCharactersList();
            }
        }

        function switchCharacterTab(tab) {
            document.querySelectorAll('.character-panel-tab').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            
            if (tab === 'list') {
                document.getElementById('character-list-tab').style.display = 'block';
                document.getElementById('character-graph-tab').style.display = 'none';
            } else {
                document.getElementById('character-list-tab').style.display = 'none';
                document.getElementById('character-graph-tab').style.display = 'block';
                renderRelationshipGraph();
            }
        }

        function renderCharacterList() {
            const container = document.getElementById('character-list');
            container.innerHTML = '';
            
            if (charactersData.length === 0) {
                container.innerHTML = '<p style="color: rgba(0, 255, 136, 0.5); text-align: center; padding: 20px;">暂无角色，点击下方按钮添加</p>';
                return;
            }
            
            charactersData.forEach(char => {
                const card = document.createElement('div');
                card.className = 'character-card-mini';
                card.onclick = () => showCharacterDetail(char.id);
                
                const statusClass = (char.status && char.status.current_state) || char.status || 'active';
                const statusText = statusClass === 'active' ? '活跃' : statusClass === 'inactive' ? '非活跃' : '已故';
                
                card.innerHTML = `
                    <div class="character-card-mini-header">
                        <div class="character-avatar">${char.avatar ? '' : '👤'}</div>
                        <div class="character-info">
                            <h4>${char.name}</h4>
                            <p class="title">${char.title || ''}</p>
                        </div>
                        <span class="character-status ${statusClass}">${statusText}</span>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        async function showCharacterDetail(charId) {
            currentCharacterId = charId;
            const char = charactersData.find(c => c.id === charId);
            if (!char) return;
            
            document.getElementById('detail-avatar').textContent = char.avatar ? '' : '👤';
            document.getElementById('detail-name').textContent = char.name;
            document.getElementById('detail-title').textContent = char.title || '无称号';
            document.getElementById('detail-description').textContent = char.description || '暂无描述';
            document.getElementById('detail-personality').textContent = char.personality || '暂无性格描述';
            
            const attrs = char.attributes || { health: 100, mana: 100, strength: 10, intelligence: 10, charisma: 10 };
            const attrsContainer = document.getElementById('detail-attributes');
            attrsContainer.innerHTML = `
                <div class="attribute-bar">
                    <span class="attribute-label">HP</span>
                    <div class="attribute-track"><div class="attribute-fill" style="width: ${Math.min(attrs.health, 200) / 2}%"></div></div>
                    <span class="attribute-value">${attrs.health}</span>
                </div>
                <div class="attribute-bar">
                    <span class="attribute-label">MP</span>
                    <div class="attribute-track"><div class="attribute-fill" style="width: ${Math.min(attrs.mana, 200) / 2}%"></div></div>
                    <span class="attribute-value">${attrs.mana}</span>
                </div>
                <div class="attribute-bar">
                    <span class="attribute-label">力量</span>
                    <div class="attribute-track"><div class="attribute-fill" style="width: ${attrs.strength}%"></div></div>
                    <span class="attribute-value">${attrs.strength}</span>
                </div>
                <div class="attribute-bar">
                    <span class="attribute-label">智力</span>
                    <div class="attribute-track"><div class="attribute-fill" style="width: ${attrs.intelligence}%"></div></div>
                    <span class="attribute-value">${attrs.intelligence}</span>
                </div>
                <div class="attribute-bar">
                    <span class="attribute-label">魅力</span>
                    <div class="attribute-track"><div class="attribute-fill" style="width: ${attrs.charisma}%"></div></div>
                    <span class="attribute-value">${attrs.charisma}</span>
                </div>
            `;
            
            const skills = char.skills || [];
            const skillsContainer = document.getElementById('detail-skills');
            if (skills.length === 0) {
                skillsContainer.innerHTML = '<p style="color: rgba(0, 255, 136, 0.5);">暂无技能</p>';
            } else {
                skillsContainer.innerHTML = skills.map(s => `
                    <div class="skill-item">
                        <span class="skill-name">${s.name}</span>
                        <span class="skill-level">Lv.${s.level}</span>
                    </div>
                `).join('');
            }
            
            const charRelations = relationsData.filter(r => r.source_id === charId || r.target_id === charId);
            const relationsContainer = document.getElementById('detail-relations');
            if (charRelations.length === 0) {
                relationsContainer.innerHTML = '<p style="color: rgba(0, 255, 136, 0.5);">暂无关系</p>';
            } else {
                relationsContainer.innerHTML = charRelations.map(r => {
                    const typeInfo = relationTypes[r.relation_type] || relationTypes.neutral;
                    const otherChar = charactersData.find(c => c.id === (r.source_id === charId ? r.target_id : r.source_id));
                    return `
                        <div class="relation-item">
                            <span class="relation-icon">${typeInfo.icon}</span>
                            <div class="relation-info">
                                <span class="relation-type-name">${otherChar ? otherChar.name : '未知'} - ${typeInfo.name}</span>
                                <span class="relation-desc">${r.description || ''}</span>
                            </div>
                            <div class="relation-strength">
                                <div class="relation-strength-fill" style="width: ${r.strength}%"></div>
                            </div>
                        </div>
                    `;
                }).join('');
            }
            
            document.getElementById('character-detail-modal').classList.add('open');
        }

        function closeCharacterDetail() {
            document.getElementById('character-detail-modal').classList.remove('open');
            currentCharacterId = null;
        }

        function showCharacterForm(charId = null) {
            document.getElementById('form-title').textContent = charId ? '编辑角色' : '添加角色';
            document.getElementById('form-char-id').value = charId || '';
            
            if (charId) {
                const char = charactersData.find(c => c.id === charId);
                if (char) {
                    document.getElementById('form-name').value = char.name;
                    document.getElementById('form-title-input').value = char.title || '';
                    document.getElementById('form-description').value = char.description || '';
                    document.getElementById('form-personality').value = char.personality || '';
                    document.getElementById('form-background').value = char.background || '';
                    const attrs = char.attributes || {};
                    document.getElementById('form-health').value = attrs.health || 100;
                    document.getElementById('form-mana').value = attrs.mana || 100;
                    document.getElementById('form-strength').value = attrs.strength || 10;
                    document.getElementById('form-intelligence').value = attrs.intelligence || 10;
                    document.getElementById('form-charisma').value = attrs.charisma || 10;
                    document.getElementById('form-status').value = char.status || 'active';
                }
            } else {
                document.getElementById('character-form').reset();
            }
            
            document.getElementById('character-form-modal').classList.add('open');
        }

        function closeCharacterForm() {
            document.getElementById('character-form-modal').classList.remove('open');
        }

        async function saveCharacter(event) {
            event.preventDefault();
            
            const charId = document.getElementById('form-char-id').value;
            const character = {
                name: document.getElementById('form-name').value,
                title: document.getElementById('form-title-input').value,
                description: document.getElementById('form-description').value,
                personality: document.getElementById('form-personality').value,
                background: document.getElementById('form-background').value,
                attributes: {
                    health: parseInt(document.getElementById('form-health').value) || 100,
                    mana: parseInt(document.getElementById('form-mana').value) || 100,
                    strength: parseInt(document.getElementById('form-strength').value) || 10,
                    intelligence: parseInt(document.getElementById('form-intelligence').value) || 10,
                    charisma: parseInt(document.getElementById('form-charisma').value) || 10
                },
                status: document.getElementById('form-status').value
            };
            
            try {
                let response;
                if (charId) {
                    response = await apiFetch(`/api/characters/${charId}`, {
                        method: 'PUT',
                        body: JSON.stringify(character)
                    });
                } else {
                    response = await apiFetch('/api/characters', {
                        method: 'POST',
                        body: JSON.stringify(character)
                    });
                }
                
                const data = await response.json();
                if (data.success || data.character) {
                    closeCharacterForm();
                    await loadCharactersList();
                } else {
                    showError('保存失败', data.error || '未知错误');
                }
            } catch (e) {
                showError('保存失败', '网络错误: ' + e.message);
            }
        }

        function editCharacter() {
            if (currentCharacterId) {
                closeCharacterDetail();
                showCharacterForm(currentCharacterId);
            }
        }

        async function deleteCharacter() {
            if (!currentCharacterId) return;
            if (!confirm('确定要删除这个角色吗？相关的所有关系也会被删除。')) return;
            
            try {
                const response = await apiFetch(`/api/characters/${currentCharacterId}`, { method: 'DELETE' });
                const data = await response.json();
                if (data.success) {
                    closeCharacterDetail();
                    await loadCharactersList();
                } else {
                    showError('删除失败', data.error || '未知错误');
                }
            } catch (e) {
                showError('删除失败', '网络错误: ' + e.message);
            }
        }

        function showRelationForm() {
            const sourceSelect = document.getElementById('relation-source');
            const targetSelect = document.getElementById('relation-target');
            const typeSelect = document.getElementById('relation-type');
            
            const options = charactersData.map(c => `<option value="${c.id}">${c.name}</option>`).join('');
            sourceSelect.innerHTML = options;
            targetSelect.innerHTML = options;
            
            const typeOptions = Object.entries(relationTypes).map(([key, val]) => 
                `<option value="${key}">${val.icon} ${val.name}</option>`
            ).join('');
            typeSelect.innerHTML = typeOptions;
            
            document.getElementById('relation-form').reset();
            document.getElementById('relation-form-modal').classList.add('open');
        }

        function closeRelationForm() {
            document.getElementById('relation-form-modal').classList.remove('open');
        }

        async function saveRelation(event) {
            event.preventDefault();
            
            const relation = {
                source_id: document.getElementById('relation-source').value,
                target_id: document.getElementById('relation-target').value,
                relation_type: document.getElementById('relation-type').value,
                strength: parseInt(document.getElementById('relation-strength').value) || 50,
                description: document.getElementById('relation-description').value
            };
            
            if (relation.source_id === relation.target_id) {
                showError('错误', '源角色和目标角色不能相同');
                return;
            }
            
            try {
                const response = await apiFetch('/api/relations', {
                    method: 'POST',
                    body: JSON.stringify(relation)
                });
                const data = await response.json();
                if (data.success) {
                    closeRelationForm();
                    await loadCharactersList();
                    renderRelationshipGraph();
                } else {
                    showError('保存失败', data.error || '未知错误');
                }
            } catch (e) {
                showError('保存失败', '网络错误: ' + e.message);
            }
        }

        function renderGraphLegend() {
            const container = document.getElementById('graph-legend');
            container.innerHTML = Object.entries(relationTypes).slice(0, 6).map(([key, val]) => `
                <div class="legend-item">
                    <div class="legend-color" style="background: ${val.color}"></div>
                    <span>${val.name}</span>
                </div>
            `).join('');
        }

        async function renderRelationshipGraph() {
            try {
                const response = await apiFetch('/api/characters/graph');
                const data = await response.json();
                const { nodes, edges } = data;
                
                const canvas = document.getElementById('graph-canvas');
                const ctx = canvas.getContext('2d');
                
                canvas.width = canvas.offsetWidth;
                canvas.height = canvas.offsetHeight;
                
                if (nodes.length === 0) {
                    ctx.fillStyle = 'rgba(0, 255, 136, 0.5)';
                    ctx.font = '14px monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText('暂无角色数据', canvas.width / 2, canvas.height / 2);
                    return;
                }
                
                const graphNodes = nodes.map((n, i) => ({
                    ...n,
                    x: canvas.width / 2 + Math.cos(2 * Math.PI * i / nodes.length) * 120,
                    y: canvas.height / 2 + Math.sin(2 * Math.PI * i / nodes.length) * 120,
                    vx: 0,
                    vy: 0
                }));
                
                const iterations = 100;
                const repulsion = 3000;
                const attraction = 0.005;
                const damping = 0.85;
                
                for (let iter = 0; iter < iterations; iter++) {
                    for (let j = 0; j < graphNodes.length; j++) {
                        for (let k = j + 1; k < graphNodes.length; k++) {
                            const dx = graphNodes[k].x - graphNodes[j].x;
                            const dy = graphNodes[k].y - graphNodes[j].y;
                            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                            const force = repulsion / (dist * dist);
                            graphNodes[j].vx -= dx / dist * force;
                            graphNodes[j].vy -= dy / dist * force;
                            graphNodes[k].vx += dx / dist * force;
                            graphNodes[k].vy += dy / dist * force;
                        }
                    }
                    
                    for (const edge of edges) {
                        const source = graphNodes.find(n => n.id === edge.source);
                        const target = graphNodes.find(n => n.id === edge.target);
                        if (source && target) {
                            const dx = target.x - source.x;
                            const dy = target.y - source.y;
                            const dist = Math.sqrt(dx * dx + dy * dy) || 1;
                            const force = dist * attraction;
                            source.vx += dx * force;
                            source.vy += dy * force;
                            target.vx -= dx * force;
                            target.vy -= dy * force;
                        }
                    }
                    
                    for (const node of graphNodes) {
                        node.vx *= damping;
                        node.vy *= damping;
                        node.x += node.vx;
                        node.y += node.vy;
                        node.x = Math.max(40, Math.min(canvas.width - 40, node.x));
                        node.y = Math.max(40, Math.min(canvas.height - 40, node.y));
                    }
                }
                
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                
                for (const edge of edges) {
                    const source = graphNodes.find(n => n.id === edge.source);
                    const target = graphNodes.find(n => n.id === edge.target);
                    if (source && target) {
                        ctx.beginPath();
                        ctx.moveTo(source.x, source.y);
                        ctx.lineTo(target.x, target.y);
                        ctx.strokeStyle = edge.color || '#00ff88';
                        ctx.lineWidth = Math.max(1, edge.strength / 30);
                        ctx.stroke();
                        
                        const angle = Math.atan2(target.y - source.y, target.x - source.x);
                        const arrowLen = 10;
                        const arrowX = target.x - Math.cos(angle) * 25;
                        const arrowY = target.y - Math.sin(angle) * 25;
                        ctx.beginPath();
                        ctx.moveTo(arrowX, arrowY);
                        ctx.lineTo(arrowX - arrowLen * Math.cos(angle - 0.5), arrowY - arrowLen * Math.sin(angle - 0.5));
                        ctx.lineTo(arrowX - arrowLen * Math.cos(angle + 0.5), arrowY - arrowLen * Math.sin(angle + 0.5));
                        ctx.closePath();
                        ctx.fillStyle = edge.color || '#00ff88';
                        ctx.fill();
                    }
                }
                
                for (const node of graphNodes) {
                    ctx.beginPath();
                    ctx.arc(node.x, node.y, 20, 0, Math.PI * 2);
                    ctx.fillStyle = node.status === 'active' ? 'rgba(0, 255, 136, 0.3)' : 
                                   node.status === 'deceased' ? 'rgba(255, 68, 68, 0.3)' : 'rgba(136, 136, 136, 0.3)';
                    ctx.fill();
                    ctx.strokeStyle = node.status === 'active' ? '#00ff88' : 
                                     node.status === 'deceased' ? '#ff4444' : '#888888';
                    ctx.lineWidth = 2;
                    ctx.stroke();
                    
                    ctx.fillStyle = '#00ff88';
                    ctx.font = '12px monospace';
                    ctx.textAlign = 'center';
                    ctx.fillText(node.name.substring(0, 4), node.x, node.y + 35);
                }
                
            } catch (e) {
                console.error('渲染关系图失败:', e);
            }
        }

        async function initApp() {
            const hasPlayer = await loadPlayerCharacter();
            showStartScreen();
        }

        let saveSlots = [];

        async function loadSaveSlots() {
            try {
                const response = await apiFetch('/api/save/list');
                const data = await response.json();
                if (data.success) {
                    saveSlots = data.saves;
                    renderSaveSlots();
                }
            } catch (error) {
                console.error('加载存档列表失败:', error);
            }
        }

        function renderSaveSlots() {
            const container = document.getElementById('save-slots');
            container.innerHTML = '';
            
            saveSlots.forEach(slot => {
                const slotDiv = document.createElement('div');
                slotDiv.className = 'save-slot' + (slot.has_save ? '' : ' empty');
                
                if (slot.has_save) {
                    const date = new Date(slot.timestamp);
                    const dateStr = date.toLocaleString('zh-CN');
                    
                    slotDiv.innerHTML = `
                        <div class="save-slot-info">
                            <h3>${slot.save_name}</h3>
                            <p>章节: ${slot.chapter} | ${slot.world_setting || '无世界观'}</p>
                            <p>时间: ${dateStr}</p>
                        </div>
                        <div class="save-slot-actions">
                            <button class="btn-load" onclick="loadSave('${slot.slot_id}')">加载</button>
                            <button class="btn-save" onclick="showSaveDialog('${slot.slot_id}')">覆盖</button>
                            <button class="btn-delete" onclick="deleteSave('${slot.slot_id}')">删除</button>
                        </div>
                    `;
                } else {
                    slotDiv.innerHTML = `
                        <div class="save-slot-info">
                            <h3>${slot.save_name}</h3>
                            <p>空存档位</p>
                        </div>
                        <div class="save-slot-actions">
                            <button class="btn-save" onclick="showSaveDialog('${slot.slot_id}')">新建存档</button>
                        </div>
                    `;
                }
                
                container.appendChild(slotDiv);
            });
        }

        function showSaveModal() {
            loadSaveSlots();
            document.getElementById('save-modal').classList.add('active');
        }

        function closeSaveModal() {
            document.getElementById('save-modal').classList.remove('active');
        }

        async function showGamesListModal() {
            await loadGamesList();
            document.getElementById('games-list-modal').classList.add('active');
        }

        function closeGamesListModal() {
            document.getElementById('games-list-modal').classList.remove('active');
        }

        async function loadGamesList() {
            try {
                const response = await apiFetch('/api/games');
                const data = await response.json();
                renderGamesList(data.games);
            } catch (error) {
                console.error('加载游戏列表失败:', error);
            }
        }

        function renderGamesList(games) {
            const container = document.getElementById('games-list');
            container.innerHTML = '';
            
            if (games.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: #888;">暂无游戏记录</p>';
                return;
            }
            
            games.forEach(game => {
                const gameDiv = document.createElement('div');
                gameDiv.className = 'save-slot';
                
                const date = new Date(game.created_at);
                const dateStr = date.toLocaleString('zh-CN');
                
                gameDiv.innerHTML = `
                    <div class="save-slot-info">
                        <h3>${game.game_id}</h3>
                        <p>${game.world_setting ? game.world_setting.substring(0, 50) + '...' : '无世界观'}</p>
                        <p>创建时间: ${dateStr}</p>
                    </div>
                    <div class="save-slot-actions">
                        <button class="btn-load" onclick="loadGame('${game.game_id}')">加载</button>
                        <button class="btn-delete" onclick="deleteGame('${game.game_id}')">删除</button>
                    </div>
                `;
                
                container.appendChild(gameDiv);
            });
        }

        async function loadGame(gameId) {
            try {
                const response = await apiFetch(`/api/games/load/${gameId}`, {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success) {
                    closeGamesListModal();
                    worldSetting = data.game_info?.world_setting || '';
                    document.getElementById('world-setting').value = worldSetting;
                    
                    const playerResponse = await apiFetch('/api/player');
                    const playerData = await playerResponse.json();
                    if (playerData.exists) {
                        playerCharacter = playerData.player;
                        showCharacterReviewScreen();
                    } else {
                        showScreen('start-screen');
                    }
                }
            } catch (error) {
                console.error('加载游戏失败:', error);
                alert('加载游戏失败');
            }
        }

        async function deleteGame(gameId) {
            if (!confirm('确定要删除这个游戏吗？此操作不可恢复。')) {
                return;
            }
            
            try {
                const response = await apiFetch(`/api/games/${gameId}`, {
                    method: 'DELETE'
                });
                const data = await response.json();
                
                if (data.success) {
                    await loadGamesList();
                }
            } catch (error) {
                console.error('删除游戏失败:', error);
            }
        }

        function showSaveDialog(slotId) {
            // Find existing save name, or default
            const savesContainer = document.getElementById('save-slots');
            const slotElement = Array.from(savesContainer.querySelectorAll('.save-slot')).find(el => {
                const btn = el.querySelector('.btn-save');
                return btn && btn.getAttribute('onclick') && btn.getAttribute('onclick').includes(`'${slotId}'`);
            });
            let defaultName = `存档 ${slotId}`;
            if (slotElement) {
                const nameStr = slotElement.querySelector('h3').textContent;
                if (nameStr && nameStr !== '空存档') {
                    defaultName = nameStr;
                }
            }

            const saveName = prompt('请输入存档名称:', defaultName);
            if (saveName) {
                saveGame(slotId, saveName);
            }
        }

        async function saveGame(slotId, saveName) {
            try {
                const saveData = {
                    slot_id: slotId,
                    save_name: saveName,
                    world_setting: worldSetting,
                    chapter: chapter,
                    messages: messages,
                    logs: logs,
                    current_scene: currentScene,
                    current_choices: currentChoices || [],
                    player: playerCharacter,
                    characters: window.charactersData || [],
                    relations: window.relationsData || [],
                    ending_triggered: endingTriggered,
                    ending_countdown: endingCountdown,
                    selected_ending_type: selectedEndingType,
                    preview_scene: currentScene ? currentScene.substring(0, 100) : '',
                    route_scores: routeScores,
                    key_decisions: keyDecisions,
                    ending_omen_state: endingOmenState
                };

                const response = await apiFetch(`/api/save/${slotId}`, {
                    method: 'POST',
                    body: JSON.stringify(saveData)
                });

                const data = await response.json();
                if (data.success) {
                    alert('存档成功!');
                    loadSaveSlots();
                }
            } catch (error) {
                console.error('保存失败:', error);
                alert('保存失败');
            }
        }

        async function loadSave(slotId) {
            try {
                const response = await apiFetch(`/api/save/load/${slotId}`, { method: 'POST' });
                const data = await response.json();
                
                if (data.success && data.save) {
                    const save = data.save;
                    
                    messages = save.messages || [];
                    chapter = save.chapter || 1;
                    logs = save.logs || [];
                    currentScene = save.current_scene;
                    currentChoices = save.current_choices || [];
                    worldSetting = save.world_setting || '';
                    endingTriggered = save.ending_triggered || false;
                    endingCountdown = save.ending_countdown || 0;
                    selectedEndingType = save.selected_ending_type || '';
                    playerCharacter = save.player || null;
                    routeScores = save.route_scores || { redemption: 0, power: 0, sacrifice: 0, betrayal: 0, retreat: 0 };
                    keyDecisions = save.key_decisions || [];
                    endingOmenState = save.ending_omen_state || {};
                    window.charactersData = save.characters || [];
                    window.relationsData = save.relations || [];

                    showScreen('game-screen');
                    document.getElementById('chapter-num').textContent = chapter;
                    
                    _renderLogEntries(logs);

                    if (currentScene) {
                        document.getElementById('scene-text').textContent = currentScene;
                    }

                    if (currentChoices && currentChoices.length > 0) {
                        _renderChoiceItems(currentChoices);
                    }

                    closeSaveModal();
                    const undoBtnLoad = document.getElementById('undo-btn');
                    if (undoBtnLoad) {
                        undoBtnLoad.style.display = 'flex';
                    }
                    updateUndoButton();
                    updatePlayerPanel();
                    alert('加载成功!');
                }
            } catch (error) {
                console.error('加载失败:', error);
                alert('加载失败');
            }
        }

        async function deleteSave(slotId) {
            if (confirm('确定要删除这个存档吗?')) {
                try {
                    const response = await apiFetch(`/api/save/${slotId}`, {
                        method: 'DELETE'
                    });
                    const data = await response.json();
                    if (data.success) {
                        loadSaveSlots();
                        alert('删除成功');
                    }
                } catch (error) {
                    console.error('删除失败:', error);
                    alert('删除失败');
                }
            }
        }

        async function pushHistory(snapshot) {
            try {
                await apiFetch('/api/history', {
                    method: 'POST',
                    body: JSON.stringify(snapshot)
                });
                updateUndoButton();
            } catch (error) {
                console.error('保存历史失败:', error);
            }
        }

        async function undoMove() {
            try {
                const response = await apiFetch('/api/history/undo', {
                    method: 'POST'
                });
                const data = await response.json();
                
                if (data.success && data.snapshot) {
                    const snapshot = data.snapshot;
                    
                    messages = snapshot.messages || [];
                    chapter = snapshot.chapter || 1;
                    currentScene = snapshot.current_scene;
                    currentChoices = snapshot.current_choices || [];
                    playerCharacter = snapshot.player || null;
                    routeScores = snapshot.route_scores || { redemption: 0, power: 0, sacrifice: 0, betrayal: 0, retreat: 0 };
                    keyDecisions = snapshot.key_decisions || [];
                    endingOmenState = snapshot.ending_omen_state || {};

                    logs = snapshot.logs != null ? JSON.parse(JSON.stringify(snapshot.logs)) : logs.slice(0, chapter - 1);

                    document.getElementById('chapter-num').textContent = chapter;

                    _renderLogEntries(logs);

                    if (currentScene) {
                        document.getElementById('scene-text').textContent = currentScene;
                    }

                    if (currentChoices && currentChoices.length > 0) {
                        _renderChoiceItems(currentChoices);
                    } else {
                        document.getElementById('choices-container').innerHTML = '';
                    }

                    saveGameState();
                    updatePlayerPanel();
                    updateUndoButton();
                }
            } catch (error) {
                console.error('回退失败:', error);
                alert('回退失败');
            }
        }

        async function updateUndoButton() {
            try {
                const response = await apiFetch('/api/history/count');
                const data = await response.json();
                if (data.success) {
                    const count = data.count;
                    const undoBtn = document.getElementById('undo-btn');
                    const undoCount = document.getElementById('undo-count');
                    if (undoCount) {
                        undoCount.textContent = count;
                    }
                    if (undoBtn) {
                        undoBtn.disabled = count === 0;
                    }
                }
            } catch (error) {
                console.error('获取历史数量失败:', error);
            }
        }


        function generatePlayerPrompt(player) {
            if (!player) return '';
            
            let prompt = '\n\n【玩家角色信息】\n';
            prompt += `姓名: ${player.name || '未知'}\n`;
            if (player.race) prompt += `种族: ${player.race}\n`;
            if (player.background) prompt += `背景: ${player.background}\n`;
            
            prompt += '\n属性:\n';
            prompt += `- 力量 ${player.strength} (修正值: ${calculateModifier(player.strength) >= 0 ? '+' : ''}${calculateModifier(player.strength)})\n`;
            prompt += `- 敏捷 ${player.dexterity} (修正值: ${calculateModifier(player.dexterity) >= 0 ? '+' : ''}${calculateModifier(player.dexterity)})\n`;
            prompt += `- 体质 ${player.constitution} (修正值: ${calculateModifier(player.constitution) >= 0 ? '+' : ''}${calculateModifier(player.constitution)})\n`;
            prompt += `- 智力 ${player.intelligence} (修正值: ${calculateModifier(player.intelligence) >= 0 ? '+' : ''}${calculateModifier(player.intelligence)})\n`;
            prompt += `- 感知 ${player.wisdom} (修正值: ${calculateModifier(player.wisdom) >= 0 ? '+' : ''}${calculateModifier(player.wisdom)})\n`;
            prompt += `- 魅力 ${player.charisma} (修正值: ${calculateModifier(player.charisma) >= 0 ? '+' : ''}${calculateModifier(player.charisma)})\n`;
            
            if (player.skills && player.skills.length > 0) {
                prompt += '\n技能:\n';
                player.skills.forEach(skill => {
                    prompt += `- ${skill.name} (等级 ${skill.level})\n`;
                });
            }
            
            return prompt;
        }


        initApp();
