#############################################################################
# workout_plan_page.py
#############################################################################

import streamlit as st
from data_fetcher import get_workout_plan

FOCUS_OPTIONS = [
    {'label': 'Chest'},
    {'label': 'Back'},
    {'label': 'Legs'},
    {'label': 'Shoulders'},
    {'label': 'Arms'},
    {'label': 'Core'},
]

LEVEL_BADGE = {
    'beginner':     ('Beginner',     '#e6f4ea', '#2d6a4f'),
    'intermediate': ('Intermediate', '#fef9e7', '#7d5a00'),
    'expert':       ('Expert',       '#fdecea', '#a00000'),
}


def display_workout_plan_page(user_id):
    st.markdown("""
        <style>
            .focus-card {
                background: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px 8px;
                text-align: center;
                cursor: pointer;
                margin-bottom: 4px;
            }
            .focus-card.active {
                border: 1.5px solid #1a1a1a;
                background: #f7f7f7;
            }
            .focus-card .emoji { font-size: 1.8rem; }
            .focus-card .label {
                font-size: 0.8rem;
                font-weight: 600;
                color: #333;
                margin-top: 6px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .badge {
                display: inline-block;
                font-size: 0.7rem;
                font-weight: 600;
                padding: 2px 10px;
                border-radius: 20px;
                margin-bottom: 6px;
            }
            .exercise-name {
                font-size: 1.05rem;
                font-weight: 700;
                color: #1a1a1a;
                margin: 0 0 4px 0;
            }
            .meta-text {
                font-size: 0.8rem;
                color: #666;
                margin: 0;
            }
        </style>
    """, unsafe_allow_html=True)

    st.title('Workout Planner')
    st.caption('AI-generated plans tailored to your fitness profile.')

    if 'workout_focus' not in st.session_state:
        st.session_state.workout_focus = None

    # Focus selection cards
    cols = st.columns(len(FOCUS_OPTIONS))
    for col, opt in zip(cols, FOCUS_OPTIONS):
        with col:
            is_active = st.session_state.workout_focus == opt['label']
            card_class = 'focus-card active' if is_active else 'focus-card'
            st.markdown(f"""
                <div class="{card_class}">
                    <div class="label">{opt['label']}</div>
                </div>
            """, unsafe_allow_html=True)
            if st.button(opt['label'], key=f"focus_{opt['label']}", use_container_width=True, type='secondary'):
                if st.session_state.workout_focus != opt['label']:
                    get_workout_plan.clear()
                st.session_state.workout_focus = opt['label']
                st.rerun()

    focus = st.session_state.workout_focus
    if not focus:
        st.markdown('<p style="color:#888;margin-top:24px;">Select a muscle group to generate your plan.</p>', unsafe_allow_html=True)
        return

    st.divider()

    with st.spinner('Generating your plan...'):
        try:
            plan = get_workout_plan(user_id, focus)
        except Exception as e:
            st.error(f'Could not generate plan: {e}')
            return

    header, regen = st.columns([4, 1])
    with header:
        st.markdown(f'**{focus} Day** &nbsp;·&nbsp; {len(plan)} exercises', unsafe_allow_html=True)
    with regen:
        if st.button('Regenerate', use_container_width=True):
            get_workout_plan.clear()
            st.rerun()

    st.write('')

    for i, ex in enumerate(plan):
        with st.container(border=True):
            img_col, info_col = st.columns([1, 2])

            with img_col:
                if ex.get('imageUrl'):
                    st.image(ex['imageUrl'], use_container_width=True)
                else:
                    st.markdown(
                        '<div style="height:140px;display:flex;align-items:center;'
                        'justify-content:center;background:#F9FAFB;border-radius:8px;">'
                        '<span style="font-size:0.8rem;color:#9CA3AF;letter-spacing:0.5px">NO IMAGE</span></div>',
                        unsafe_allow_html=True,
                    )

            with info_col:
                level = ex.get('level', '')
                badge_label, badge_bg, badge_color = LEVEL_BADGE.get(level, ('', '#eee', '#555'))

                if badge_label:
                    st.markdown(
                        f'<span class="badge" style="background:{badge_bg};color:{badge_color};">'
                        f'{badge_label}</span>',
                        unsafe_allow_html=True,
                    )

                st.markdown(f'<p class="exercise-name">{i + 1}. {ex["name"].title()}</p>', unsafe_allow_html=True)
                st.markdown(
                    f'<p class="meta-text">{", ".join(m.title() for m in ex["primaryMuscles"])} &nbsp;·&nbsp; {ex["equipment"].title()}</p>',
                    unsafe_allow_html=True,
                )

                st.write('')
                c1, c2 = st.columns(2)
                c1.metric('Sets', ex['sets'])
                c2.metric('Reps', ex['reps'])

                if ex.get('tip'):
                    st.caption(ex['tip'])

            if ex.get('instructions'):
                with st.expander('Instructions'):
                    for step, line in enumerate(ex['instructions'], 1):
                        st.markdown(f'{step}. {line}')
