import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/lib/supabase";

const AuthCallback = () => {
  const navigate = useNavigate();

  useEffect(() => {
    const handleAuthCallback = async () => {
      const { data: sessionData } = await supabase.auth.getSession();
      
      if (sessionData?.session) {
        navigate('/', { replace: true });
      } else {
        navigate('/auth/login', { replace: true });
      }
    };

    handleAuthCallback();
  }, [navigate]);

  return null;
};

export default AuthCallback;
