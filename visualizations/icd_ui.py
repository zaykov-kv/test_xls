import streamlit as st
from core.icd_api import get_icd10_code_details


def render_code_validation(all_results):
    """Поиск информации о конкретном коде МКБ-10 через API."""
    with st.expander("🔍 Проверка кода МКБ-10", expanded=False):
        st.markdown("**Поиск информации о коде МКБ-10**")
        st.caption("💡 Введите код для проверки (например, E11.9, I10, C50)")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            icd_code = st.text_input(
                "Введите код МКБ-10:",
                placeholder="Например: E11.9, I10, C50",
                key="icd_code_search"
            )
        
        with col2:
            search_btn = st.button("🔍 Найти код", use_container_width=True, type="primary")
        
        if search_btn and icd_code:
            with st.spinner("⏳ Поиск кода..."):
                code_clean = icd_code.strip().upper()
                details = get_icd10_code_details(code_clean)
                
                if details:
                    st.success(f"✅ Код **{code_clean}** найден")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("📋 Код", details.get("code", code_clean))
                    with col2:
                        st.metric("📝 Статус", "✅ Корректен")
                    
                    st.info(f"**Описание:** {details.get('description', 'Описание не найдено')}")
                else:
                    st.warning(f"❌ Код **{code_clean}** не найден. Проверьте правильность ввода.")
        
        st.markdown("---")
        st.markdown("**📌 Часто используемые коды:**")
        
        common_codes = [
            ("E11.9", "Сахарный диабет 2 типа без осложнений"),
            ("I10", "Эссенциальная гипертензия"),
            ("I50", "Сердечная недостаточность"),
            ("J44", "Хроническая обструктивная болезнь легких"),
            ("C50", "Злокачественное новообразование молочной железы"),
            ("N18", "Хроническая почечная недостаточность"),
            ("F10", "Алкоголизм"),
            ("E66", "Ожирение")
        ]
        
        cols = st.columns(4)
        for idx, (code, desc) in enumerate(common_codes):
            with cols[idx % 4]:
                if st.button(f"📋 {code}", key=f"common_{code}"):
                    st.session_state.icd_code_search = code
                    st.rerun()