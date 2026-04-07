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

-- 3. Actualizar Tabla de Sesiones (Si ya existe)
ALTER TABLE public.sessions ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES public.users_profiles(id) ON DELETE CASCADE;

-- 4. Funciones Auxiliares para creación de usuario y código amigo
CREATE OR REPLACE FUNCTION generate_friend_code()
RETURNS TEXT AS $$
DECLARE
    new_code TEXT;
    done BOOL;
BEGIN
    done := false;
    WHILE NOT done LOOP
        new_code := lpad(floor(random() * 1000000)::text, 6, '0');
        IF NOT EXISTS (SELECT 1 FROM public.users_profiles WHERE friend_code = new_code) THEN
            done := true;
        END IF;
    END LOOP;
    RETURN new_code;
END;
$$ LANGUAGE plpgsql VOLATILE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.handle_new_user() 
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users_profiles (id, email, display_name, friend_code)
  VALUES (
      new.id, 
      new.email, 
      split_part(new.email, '@', 1), -- Toma lo que viene antes del @ del email como nombre por defecto
      generate_friend_code()
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Recrear el trigger
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();

-- ==========================================
-- POLÍTICAS DE SEGURIDAD (RLS)
-- ==========================================

ALTER TABLE public.users_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.friends ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.sessions ENABLE ROW LEVEL SECURITY;

-- POLÍTICAS: users_profiles
CREATE POLICY "Cualquiera puede ver perfiles" 
    ON public.users_profiles FOR SELECT 
    USING ( auth.role() = 'authenticated' );

CREATE POLICY "Usuarios pueden actualizar su propio perfil" 
    ON public.users_profiles FOR UPDATE 
    USING ( auth.uid() = id );

-- POLÍTICAS: friends
CREATE POLICY "Usuarios pueden ver sus propios amigos o solicitudes" 
    ON public.friends FOR SELECT 
    USING ( auth.uid() = user_id OR auth.uid() = friend_id );

CREATE POLICY "Usuarios pueden enviar solicitudes de amistad" 
    ON public.friends FOR INSERT 
    WITH CHECK ( auth.uid() = user_id );

CREATE POLICY "Usuarios pueden aceptar solicitudes recibidas" 
    ON public.friends FOR UPDATE 
    USING ( auth.uid() = friend_id AND status = 'pending' )
    WITH CHECK ( status = 'accepted' );

CREATE POLICY "Usuarios pueden borrar a sus amigos (desamigar)"
    ON public.friends FOR DELETE
    USING ( auth.uid() = user_id OR auth.uid() = friend_id );

-- POLÍTICAS: sessions
CREATE POLICY "Usuarios pueden insertar sus propias sesiones" 
    ON public.sessions FOR INSERT 
    WITH CHECK ( auth.uid() = user_id );

CREATE POLICY "Usuarios pueden actualizar sus propias sesiones" 
    ON public.sessions FOR UPDATE 
    USING ( auth.uid() = user_id );

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
