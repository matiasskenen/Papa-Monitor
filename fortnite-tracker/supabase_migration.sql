-- ==========================================
-- SCRIPT DE MIGRACIÓN: MULTI-USUARIO Y AMIGOS
-- Ejecutar en el panel SQL de Supabase
-- ==========================================

-- 1. Crear Tabla de Perfiles
CREATE TABLE IF NOT EXISTS public.users_profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    friend_code TEXT UNIQUE,
    pinned_friend_id UUID REFERENCES public.users_profiles(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Crear Tabla de Amigos
CREATE TABLE IF NOT EXISTS public.friends (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users_profiles(id) ON DELETE CASCADE,
    friend_id UUID REFERENCES public.users_profiles(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    UNIQUE(user_id, friend_id)
);

-- 3. Crear o Actualizar Tabla de Sesiones (Crucial por si es un proyecto Supabase totalmente nuevo)
CREATE TABLE IF NOT EXISTS public.sessions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES public.users_profiles(id) ON DELETE CASCADE,
    is_active BOOLEAN DEFAULT false,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    end_time TIMESTAMP WITH TIME ZONE,
    last_heartbeat TIMESTAMP WITH TIME ZONE
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sessions' AND column_name='user_id') THEN
        ALTER TABLE public.sessions ADD COLUMN user_id UUID REFERENCES public.users_profiles(id) ON DELETE CASCADE;
    END IF;
END $$;

-- 4. Funciones Auxiliares para creación de usuario y código amigo
CREATE OR REPLACE FUNCTION public.generate_friend_code()
RETURNS TEXT AS $$
DECLARE
    new_code TEXT;
    done BOOL;
    safe_counter INT := 0;
BEGIN
    done := false;
    WHILE NOT done AND safe_counter < 100 LOOP
        new_code := lpad(floor(random() * 1000000)::text, 6, '0');
        IF NOT EXISTS (SELECT 1 FROM public.users_profiles WHERE friend_code = new_code) THEN
            done := true;
        END IF;
        safe_counter := safe_counter + 1;
    END LOOP;
    RETURN new_code;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
DECLARE
  default_name TEXT;
BEGIN
  default_name := COALESCE(split_part(new.email, '@', 1), 'Usuario');
  
  INSERT INTO public.users_profiles (id, email, display_name, friend_code)
  VALUES (
      new.id, 
      COALESCE(new.email, 'user_' || substr(new.id::text, 1, 8) || '@app.com'), 
      default_name,
      public.generate_friend_code()
  );
  RETURN new;
EXCEPTION WHEN OTHERS THEN
  -- En caso de error, RAISE NOTICE para debug en logs de supabase
  -- Pero retornamos NEW para no romper el flujo de Auth
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recrear el trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ==========================================
-- POLÍTICAS DE SEGURIDAD (RLS)
-- ==========================================

ALTER TABLE public.users_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friends ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- POLÍTICAS: users_profiles
DROP POLICY IF EXISTS "Cualquiera puede ver perfiles" ON public.users_profiles;
CREATE POLICY "Cualquiera puede ver perfiles" 
    ON public.users_profiles FOR SELECT 
    USING ( auth.role() = 'authenticated' );

DROP POLICY IF EXISTS "Usuarios pueden actualizar su propio perfil" ON public.users_profiles;
CREATE POLICY "Usuarios pueden actualizar su propio perfil" 
    ON public.users_profiles FOR UPDATE 
    USING ( auth.uid() = id );

-- POLÍTICAS: friends
DROP POLICY IF EXISTS "Usuarios pueden ver sus propios amigos o solicitudes" ON public.friends;
CREATE POLICY "Usuarios pueden ver sus propios amigos o solicitudes" 
    ON public.friends FOR SELECT 
    USING ( auth.uid() = user_id OR auth.uid() = friend_id );

DROP POLICY IF EXISTS "Usuarios pueden enviar solicitudes de amistad" ON public.friends;
CREATE POLICY "Usuarios pueden enviar solicitudes de amistad" 
    ON public.friends FOR INSERT 
    WITH CHECK ( auth.uid() = user_id );

DROP POLICY IF EXISTS "Usuarios pueden aceptar solicitudes recibidas" ON public.friends;
CREATE POLICY "Usuarios pueden aceptar solicitudes recibidas" 
    ON public.friends FOR UPDATE 
    USING ( auth.uid() = friend_id AND status = 'pending' )
    WITH CHECK ( status = 'accepted' );

DROP POLICY IF EXISTS "Usuarios pueden borrar a sus amigos (desamigar)" ON public.friends;
CREATE POLICY "Usuarios pueden borrar a sus amigos (desamigar)"
    ON public.friends FOR DELETE
    USING ( auth.uid() = user_id OR auth.uid() = friend_id );

-- POLÍTICAS: sessions
DROP POLICY IF EXISTS "Usuarios pueden insertar sus propias sesiones" ON public.sessions;
CREATE POLICY "Usuarios pueden insertar sus propias sesiones" 
    ON public.sessions FOR INSERT 
    WITH CHECK ( auth.uid() = user_id );

DROP POLICY IF EXISTS "Usuarios pueden actualizar sus propias sesiones" ON public.sessions;
CREATE POLICY "Usuarios pueden actualizar sus propias sesiones" 
    ON public.sessions FOR UPDATE 
    USING ( auth.uid() = user_id );

DROP POLICY IF EXISTS "Usuarios pueden ver sus sesiones y la de sus amigos aceptados" ON public.sessions;
CREATE POLICY "Usuarios pueden ver sus sesiones y la de sus amigos aceptados" 
    ON public.sessions FOR SELECT 
    USING ( 
        auth.uid() = user_id OR
        user_id IN (
            SELECT f.friend_id 
            FROM public.friends f 
            WHERE f.user_id = auth.uid() AND f.status = 'accepted'
            UNION
            SELECT f.user_id 
            FROM public.friends f 
            WHERE f.friend_id = auth.uid() AND f.status = 'accepted'
        )
    );
