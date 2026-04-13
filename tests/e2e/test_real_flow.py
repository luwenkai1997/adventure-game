import pytest
from playwright.sync_api import Page, expect
import time

def test_full_game_flow(page: Page):
    """
    真实模拟端到端调用
    这可能会消耗几分钟的时间（包含请求、生成人物、5轮故事、编写小说）
    """
    # 增加页面加载超时
    page.set_default_timeout(180000)
    
    print("\n🚀 [Playwright] 前往游戏首页...")
    page.goto("http://localhost:8000")
    
    # 1. Start game and expand background
    print("✍️ [Playwright] 输入故事设定...")
    page.fill("#world-setting", "古代江湖")
    page.click("#expand-btn")
    
    print("⏳ [Playwright] 等待大模型扩展背景...")
    # Loading spinner disappears
    page.wait_for_selector("#expand-loading", state="hidden")
    
    # Verify expansion text
    expanded_setting = page.locator("#expanded-setting").input_value()
    assert len(expanded_setting) > 10, "大模型未返回扩展背景内容"
    
    print("🎮 [Playwright] 点击开始游戏...")
    page.click("text=开始新游戏")
    
    # Wait for the character generation to finish and transition to character review
    print("⏳ [Playwright] 等待大模型生成主角...")
    page.wait_for_selector("#character-review-screen.active")
    
    print("✅ [Playwright] 确认主角信息...")
    page.click("button[onclick='confirmCharacterReview()']")
    
    print("⏳ [Playwright] 等待大模型生成配角关系网络...")
    # Hide loading overlay and make game active
    page.wait_for_selector("#loading-overlay", state="hidden")
    page.wait_for_selector("#game-screen.active")
    
    # 2. Iterate 5 turns
    for turn in range(1, 6):
        print(f"🗡️ [Playwright] 开始执行第 {turn} 轮游戏推演...")
        
        # Wait for the choices to appear and loading to disappear
        page.wait_for_selector(".choices-container .choice-item", state="visible")
        page.wait_for_selector("#loading", state="hidden", timeout=10000)
        
        # Click the first choice available
        page.locator(".choices-container .choice-item").first.click()
        
    print("🎉 [Playwright] 第五轮推进完毕，等待最终响应稳定...")
    # Wait for the 6th choices to appear before saving so state is clean
    page.wait_for_selector(".choices-container .choice-item", state="visible")
    page.wait_for_selector("#loading", state="hidden")
    
    # 3. Save game
    print("💾 [Playwright] 呼出并执行存档流程...")
    page.locator('button:has-text("💾 存档")').click()
    page.wait_for_selector("#save-modal.active", timeout=10000)
    
    # Intercept the '请输入存档名称:' prompt dialog!
    page.once("dialog", lambda dialog: dialog.accept("save1"))
    
    # Click the save button on the first slot 
    page.locator("#save-slots .btn-save").first.click()
    
    # Wait a bit for the modal to be potentially done (toast or just hidden)
    # The modal stays open, we just manually close it.
    page.click("#save-modal .save-modal-close")
    page.wait_for_selector("#save-modal", state="hidden")
    
    # 4. Trigger ending
    print("🏁 [Playwright] 触发游戏结局...")
    page.click("#end-game-btn")
    
    # Select ending dialog
    page.wait_for_selector("#ending-select-container", state="visible")
    page.select_option("#ending-type-select", value="好结局")
    page.locator("button.ending-confirm-btn", has_text="确认").click()
    
    print("📖 [Playwright] 触发小说完整生成...")
    page.wait_for_selector("#ending-screen.active")
    page.click("#generate-novel-btn")
    
    page.wait_for_selector("#novel-modal", state="visible")
    page.click("#novel-modal-generate-btn")
    
    print("⏳ [Playwright] 正在后台生成小说全部章节，请耐心等待（通常需较长时间）...")
    page.wait_for_selector("#novel-modal-result", state="visible", timeout=300000)
    
    # Extract resulting text
    result_text = page.locator("#novel-modal-result").inner_text()
    
    print(f"🎊 [Playwright] 测试通过！最终小说生成长度：{len(result_text)} 字。")
    assert len(result_text) > 50, "小说内容提取异常(长度过短)"
    
    # Finally closing the page as specified
    page.close()
