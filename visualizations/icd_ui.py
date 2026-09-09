import streamlit as st
import pandas as pd
import re
import html
from core.icd_api import get_icd10_code_details, search_icd10_by_name, token_manager


def render_code_validation(all_results=None):
    """
    Поиск информации о коде МКБ-10.
    """
    with st.expander("🔍 Проверка кода МКБ-10", expanded=False):
        st.markdown("**Поиск информации о коде МКБ-10**")
        
        tab1, tab2 = st.tabs(["🔎 Поиск по коду", "🔍 Поиск по названию"])
        
        # ====================================================================
        # ВКЛАДКА 1: ПОИСК ПО КОДУ
        # ====================================================================
        with tab1:
            st.caption("💡 Введите код МКБ-10 (например, E11.9, I10, C50)")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                icd_code = st.text_input(
                    "Введите код МКБ-10:",
                    placeholder="Например: E11.9, I10, C50",
                    key="icd_code_search"
                )
            
            with col2:
                search_code_btn = st.button("🔍 Найти код", use_container_width=True, type="primary", key="search_code_btn")
            
            if search_code_btn and icd_code:
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
        
        # ====================================================================
        # ВКЛАДКА 2: ПОИСК ПО НАЗВАНИЮ
        # ====================================================================
        with tab2:
            st.caption("💡 Введите название на английском (например, diabetes, heart failure)")
            
            # Проверяем статус WHO API
            token = token_manager.get_token()
            if token:
                st.success("✅ WHO API доступен")
            else:
                st.warning("⚠️ WHO API недоступен. Проверьте секреты.")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                search_name = st.text_input(
                    "Введите название:",
                    placeholder="Например: diabetes, heart failure, asthma",
                    key="icd_name_search"
                )
            
            with col2:
                # Выбор количества результатов
                max_results = st.selectbox(
                    "Количество результатов:",
                    options=[10, 20, 30, 50, 100],
                    index=2,  # По умолчанию 30
                    key="max_results_select"
                )
            
            # Кнопка поиска
            search_name_btn = st.button("🔍 Найти по названию", use_container_width=True, type="primary", key="search_name_btn")
            
            if search_name_btn and search_name:
                with st.spinner(f"⏳ Поиск (до {max_results} результатов)..."):
                    results = search_icd10_by_name(search_name, max_results=max_results)
                    
                    if results:
                        st.success(f"✅ Найдено {len(results)} результатов")
                        
                        # Простой вывод в стиле Streamlit
                        for i, item in enumerate(results, 1):
                            desc = item.get('description', '')
                            desc = re.sub(r'<[^>]+>', '', desc)
                            desc = html.unescape(desc)
                            
                            st.write(f"{i}. {desc}")
                    else:
                        st.warning(f"❌ По запросу '{search_name}' ничего не найдено")
                        st.info("💡 Попробуйте использовать другое английское название")
        
        # ====================================================================
        # ЧАСТО ИСПОЛЬЗУЕМЫЕ КОДЫ
        # ====================================================================
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
                st.code(code, language="text")
                st.caption(desc[:30] + "..." if len(desc) > 30 else desc)