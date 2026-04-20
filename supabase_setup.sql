
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.user_goals (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    primary_goal     TEXT NOT NULL DEFAULT 'General Fitness',
    experience       TEXT NOT NULL DEFAULT 'Beginner',
    focus_area       TEXT NOT NULL DEFAULT 'Full Body',
    weekly_workouts  INTEGER NOT NULL DEFAULT 3,
    daily_steps_goal INTEGER NOT NULL DEFAULT 8000,
    notes            TEXT,
    updated_at       TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id)
);

ALTER TABLE public.user_goals ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own goals"
    ON public.user_goals
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ---------------------------------------------------------------------------
-- 2. body_metrics
--    One row per day per user — weight, body fat, tape measurements.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.body_metrics (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date          DATE NOT NULL,
    time          TEXT,
    weight_kg     NUMERIC(5,1),
    height_cm     NUMERIC(5,1),
    body_fat_pct  NUMERIC(4,1),
    chest_cm      NUMERIC(5,1),
    waist_cm      NUMERIC(5,1),
    hips_cm       NUMERIC(5,1),
    arms_cm       NUMERIC(4,1),
    thighs_cm     NUMERIC(4,1),
    notes         TEXT,
    UNIQUE (user_id, date)
);

ALTER TABLE public.body_metrics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own body metrics"
    ON public.body_metrics
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ---------------------------------------------------------------------------
-- 3. workout_sessions
--    Completed live workout sessions tracked via the Session tab.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workout_sessions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    date          DATE NOT NULL,
    duration_min  INTEGER DEFAULT 0,
    total_sets    INTEGER DEFAULT 0,
    cal_estimate  INTEGER DEFAULT 0,
    exercises     JSONB,   -- array of {name, sets_done, sets_target, reps}
    created_at    TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE public.workout_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own sessions"
    ON public.workout_sessions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ---------------------------------------------------------------------------
-- 4. nutrition_profiles
--    Stores the personal details entered on the Nutrition tab.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.nutrition_profiles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    weight_kg     NUMERIC(5,1),
    age           INTEGER,
    sex           TEXT,
    dietary_pref  TEXT DEFAULT 'No restriction',
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id)
);

ALTER TABLE public.nutrition_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own nutrition profile"
    ON public.nutrition_profiles
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);


-- ---------------------------------------------------------------------------
-- 5. reactions
--    Stores emoji reactions to community posts.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.reactions (
    id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id  UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    post_id  TEXT NOT NULL,
    emoji    TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (user_id, post_id, emoji)
);

ALTER TABLE public.reactions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage their own reactions"
    ON public.reactions
    FOR ALL
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Allow anyone to read reaction counts (for display)
CREATE POLICY "Anyone can read reactions"
    ON public.reactions
    FOR SELECT
    USING (true);


-- ---------------------------------------------------------------------------
-- Helpful indexes
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_body_metrics_user_date  ON public.body_metrics (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_workout_sessions_user   ON public.workout_sessions (user_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_reactions_post          ON public.reactions (post_id);


-- ---------------------------------------------------------------------------
-- Done!  Verify with:
--   SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';
-- ---------------------------------------------------------------------------
