import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/lib/supabase";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { extractJWTFromSupabaseSession, storeJWTToken, isValidToken } from "@/utils/jwt";
import { createSessionFromSupabase } from "@/utils/sessionManager";
import type { User as SupabaseUser } from "@supabase/supabase-js";

// Helper to convert Supabase user to our User type (same as in AuthContext)
const convertSupabaseUser = async (supabaseUser: SupabaseUser, skipProfileFetch = false): Promise<any | null> => {
  if (!supabaseUser) return null;

  let profile = null;
  
  if (!skipProfileFetch) {
    try {
      // Add timeout to prevent hanging
      const timeout = 2000; // 2 seconds max
      const profilePromise = supabase
        .from('user_profiles')
        .select('*')
        .eq('user_id', supabaseUser.id)
        .single();

      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('Profile fetch timeout')), timeout)
      );

      const result = await Promise.race([profilePromise, timeoutPromise]);
      const { data, error } = result;

      if (error && error.code !== 'PGRST116') {
        console.error('Error fetching user profile:', error);
      } else if (data) {
        profile = data;
      }
    } catch (error: any) {
      // Timeout or other error - continue with basic user data
      console.warn('Could not fetch user profile (continuing with basic data):', error.message || error);
    }
  }

  return {
    id: supabaseUser.id,
    email: supabaseUser.email || '',
    fullName: profile?.full_name || supabaseUser.user_metadata?.full_name || supabaseUser.user_metadata?.name || supabaseUser.email?.split('@')[0] || 'User',
    role: (profile?.role as any) || 'donor',
    dateOfBirth: profile?.date_of_birth,
    gender: profile?.gender,
    phoneNumber: profile?.phone_number,
    pan: profile?.pan,
    address: profile?.address,
    createdAt: supabaseUser.created_at,
    avatar: supabaseUser.user_metadata?.avatar_url || supabaseUser.user_metadata?.picture,
  };
};

const AuthCallback = () => {
  const navigate = useNavigate();
  const auth = useAuth();
  const { user, isLoading: authLoading, updateUser } = auth;
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(true);
  
  // Prevent recursive calls - check if already processing
  const processingKey = 'auth_callback_processing';
  
  useEffect(() => {
    // Check if already processing
    if (sessionStorage.getItem(processingKey) === 'true') {
      console.log('AuthCallback: Already processing, skipping...');
      return;
    }
    
    // Mark as processing
    sessionStorage.setItem(processingKey, 'true');
    
    let isMounted = true;
    let timeoutId: NodeJS.Timeout | null = null;
    
    const handleAuthCallback = async () => {
      try {
        console.log('AuthCallback: Starting OAuth callback processing');
        console.log('AuthCallback: Current URL:', window.location.href);
        console.log('AuthCallback: URL hash:', window.location.hash);
        console.log('AuthCallback: URL search:', window.location.search);
        
        // CRITICAL: Check URL hash FIRST - Supabase OAuth puts tokens here
        // This must be done BEFORE Supabase processes it, or we'll miss it
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const errorParam = hashParams.get('error');
        const errorDescription = hashParams.get('error_description');
        
        // If we have tokens in hash, set session immediately
        if (accessToken && refreshToken) {
          console.log('AuthCallback: Γ£à Found tokens in URL hash, setting session immediately...');
          try {
            const { data: hashSession, error: hashError } = await supabase.auth.setSession({
              access_token: accessToken,
              refresh_token: refreshToken,
            });
            
            if (hashSession?.session) {
              console.log('AuthCallback: Γ£à Session set from URL hash');
              // Clean up URL hash after setting session
              window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
              
              // Continue with normal flow using this session
              const sessionData = hashSession;
              const userId = sessionData.session.user.id;
              const userEmail = sessionData.session.user.email;
              
              // Mark as OAuth session
              sessionStorage.setItem('is_oauth_session', 'true');
              
              // Convert and set user (skip profile fetch initially for speed)
              const userData = await convertSupabaseUser(sessionData.session.user, true);
              if (userData) {
                await updateUser(userData);
                console.log('AuthCallback: Γ£à User state set (basic):', userData.email);
                
                // Fetch profile in background for redirect path
                const profilePromise = supabase
                  .from('user_profiles')
                  .select('*')
                  .eq('user_id', userId)
                  .single();
                
                const timeoutPromise = new Promise<{ data: any; error: any }>((resolve) =>
                  setTimeout(() => resolve({ data: null, error: { code: 'TIMEOUT' } }), 1500)
                );
                
                const { data: profile } = await Promise.race([profilePromise, timeoutPromise]);
                
                // Fetch full profile in background and update user
                convertSupabaseUser(sessionData.session.user, false).then(fullUserData => {
                  if (fullUserData) {
                    updateUser(fullUserData);
                    console.log('AuthCallback: Γ£à Full user profile updated (background):', fullUserData.email);
                  }
                }).catch(err => {
                  console.warn('AuthCallback: Background profile fetch failed:', err);
                });
                
                if (isMounted) {
                  setIsProcessing(false);
                  sessionStorage.removeItem(processingKey);
                  // Redirect to home page after successful login
                  navigate('/', { replace: true });
                  return;
                }
              }
            } else {
              console.error('AuthCallback: Failed to set session from hash:', hashError);
            }
          } catch (hashErr) {
            console.error('AuthCallback: Error setting session from hash:', hashErr);
          }
        }
        
        // Check for OAuth errors in hash
        if (errorParam) {
          console.error('AuthCallback: OAuth error in URL hash:', errorParam, errorDescription);
          if (isMounted) {
            setError(errorDescription || errorParam || 'OAuth authentication failed');
            setIsProcessing(false);
            sessionStorage.removeItem(processingKey);
            timeoutId = setTimeout(() => {
              if (isMounted) {
                navigate('/auth/login', { replace: true });
              }
            }, 3000);
          }
          return;
        }
        
        // Get URL parameters once at the start - will be reused later
        const urlParams = new URLSearchParams(window.location.search);
        
        // Check if this is a redirect from backend callback (has google_auth=success)
        const googleAuthSuccess = urlParams.get('google_auth') === 'success';
        
        if (googleAuthSuccess) {
          console.log('AuthCallback: Backend callback successful, checking session...');
          
          // CRITICAL: Check backend session first (cookie-based) with short timeout
          // Note: This may fail in local dev if Vercel functions aren't running
          // That's okay - we'll fall back to Supabase session check below
          try {
            const authCheckPromise = fetch('/api/auth/me', {
              method: 'GET',
              credentials: 'include', // CRITICAL: Include cookies
              headers: {
                'Content-Type': 'application/json',
              },
            });
            
            const timeoutPromise = new Promise<Response>((_, reject) =>
              setTimeout(() => reject(new Error('Backend check timeout')), 1000)
            );
            
            const authCheckResponse = await Promise.race([authCheckPromise, timeoutPromise]);
            
            if (authCheckResponse.ok) {
              const authData = await authCheckResponse.json();
              if (authData.authenticated && authData.user) {
                console.log('AuthCallback: Backend session found, setting user state...');
                await updateUser(authData.user);
                
                // Clean up URL
                window.history.replaceState({}, document.title, window.location.pathname);
                
                // Redirect to home page after successful login
                if (isMounted) {
                  setIsProcessing(false);
                  sessionStorage.removeItem(processingKey);
                  navigate('/', { replace: true });
                  return;
                }
              }
            } else {
              console.log('AuthCallback: Backend auth endpoint returned', authCheckResponse.status, '- falling back to Supabase');
            }
          } catch (checkError) {
            // Backend endpoint not available or timeout - fall through to Supabase check
            console.log('AuthCallback: Backend auth check not available/timeout, using Supabase session');
          }
        }
        
        // CRITICAL: Wait for Supabase to process the OAuth callback and establish session
        // Simplified: Check immediately, then retry once with short delay if needed
        let sessionData = null;
        let authError = null;
        
        // First, check if Supabase has already processed the session
        const immediateCheck = await supabase.auth.getSession();
        if (immediateCheck.data?.session) {
          console.log('AuthCallback: Γ£à Session already available from Supabase');
          sessionData = immediateCheck.data;
        } else {
          // Wait briefly and retry once (OAuth callback might need a moment)
          await new Promise(resolve => setTimeout(resolve, 500));
          const retryCheck = await supabase.auth.getSession();
          sessionData = retryCheck.data;
          authError = retryCheck.error;
          
          if (sessionData?.session) {
            console.log('AuthCallback: Γ£à Session found on retry');
          }
        }

        if (authError) {
          console.error('AuthCallback: Auth error:', authError);
          if (isMounted) {
            setError(authError.message || 'Authentication failed');
            setIsProcessing(false);
            sessionStorage.removeItem(processingKey);
            timeoutId = setTimeout(() => {
              if (isMounted) {
                navigate('/auth/login', { replace: true });
              }
            }, 3000);
          }
          return;
        }

        if (!sessionData?.session) {
          console.error('AuthCallback: Γ¥î No session found after all retries');
          
          // LAST RESORT: Try to get session from URL hash (Supabase OAuth callback)
          const hashParams = new URLSearchParams(window.location.hash.substring(1));
          const accessToken = hashParams.get('access_token');
          const refreshToken = hashParams.get('refresh_token');
          
          if (accessToken && refreshToken) {
            console.log('AuthCallback: Found tokens in URL hash, setting session...');
            try {
              const { data: hashSession, error: hashError } = await supabase.auth.setSession({
                access_token: accessToken,
                refresh_token: refreshToken,
              });
              
              if (hashSession?.session) {
                console.log('AuthCallback: Γ£à Session set from URL hash');
                sessionData = hashSession;
              } else {
                console.error('AuthCallback: Failed to set session from hash:', hashError);
              }
            } catch (hashErr) {
              console.error('AuthCallback: Error setting session from hash:', hashErr);
            }
          }
          
          if (!sessionData?.session) {
            if (isMounted) {
              setError('No session found. Please try signing in again.');
              setIsProcessing(false);
              sessionStorage.removeItem(processingKey);
              timeoutId = setTimeout(() => {
                if (isMounted) {
                  navigate('/auth/login', { replace: true });
                }
              }, 2000);
            }
            return;
          }
        }

        const userId = sessionData.session.user.id;
        const userEmail = sessionData.session.user.email;
        const provider = sessionData.session.user.app_metadata?.provider || 'email';

        console.log('AuthCallback: Session found for user:', userId, 'Provider:', provider);

        // CRITICAL: Clear any password reset flags - this is OAuth, not password reset
        sessionStorage.removeItem('is_password_reset_session');
        
        // CRITICAL: Mark this as an OAuth session (not password reset)
        // This helps AuthContext distinguish OAuth from password reset
        sessionStorage.setItem('is_oauth_session', 'true');
        
        // CRITICAL: Ensure session is stored in Supabase FIRST
        console.log('AuthCallback: Ensuring session is stored in Supabase...');
        await supabase.auth.setSession(sessionData.session);
        console.log('AuthCallback: ✅ Session stored in Supabase');
        
        // CRITICAL: Force user state to be set IMMEDIATELY - don't wait for anything
        console.log('AuthCallback: Setting user state immediately...');
        
        // Create basic user from session (skip profile fetch for speed)
        const basicUser = {
          id: userId,
          email: userEmail || '',
          fullName: sessionData.session.user.user_metadata?.full_name || 
                   sessionData.session.user.user_metadata?.name || 
                   userEmail?.split('@')[0] || 'User',
          role: 'donor', // Default role, will be updated in background
          createdAt: sessionData.session.user.created_at,
          avatar: sessionData.session.user.user_metadata?.avatar_url || 
                 sessionData.session.user.user_metadata?.picture,
        };
        
        // Set user state immediately
        await updateUser(basicUser);
        console.log('AuthCallback: ✅ User state set:', basicUser.email);
        
        // Store session and token
        try {
          const sessionId = await createSessionFromSupabase(sessionData.session);
          const jwtToken = extractJWTFromSupabaseSession(sessionData.session);
          if (jwtToken && sessionId) {
            storeJWTToken(jwtToken, sessionId);
            console.log('AuthCallback: ✅ Session and token stored');
          }
        } catch (tokenErr) {
          console.warn('AuthCallback: Token storage error (non-critical):', tokenErr);
        }
        
        // Clean up URL immediately
        window.history.replaceState({}, document.title, window.location.pathname);
        
        // Create profile in background (don't await - non-blocking)
        const userMetadata = sessionData.session.user.user_metadata || {};
        const fullName = userMetadata.full_name || 
                        userMetadata.name || 
                        userMetadata.display_name ||
                        (userEmail ? userEmail.split('@')[0] : 'User');
        
        supabase
          .from('user_profiles')
          .upsert({
            user_id: userId,
            full_name: fullName,
            email: userEmail || '',
            role: 'donor',
          }, {
            onConflict: 'user_id',
            ignoreDuplicates: false
          })
          .then(() => {
            console.log('AuthCallback: ✅ Profile created/updated in background');
            // Update user with full profile in background
            convertSupabaseUser(sessionData.session.user, false).then(fullUserData => {
              if (fullUserData) {
                updateUser(fullUserData);
                console.log('AuthCallback: ✅ Full user profile updated');
              }
            }).catch(() => {});
          })
          .catch(() => {}); // Silently ignore - profile can be created later
        
        // REDIRECT IMMEDIATELY - don't wait for anything else
        if (isMounted) {
          console.log('AuthCallback: 🚀 REDIRECTING to home page NOW');
          setIsProcessing(false);
          sessionStorage.removeItem(processingKey);
          // Use setTimeout to ensure state updates are processed
          setTimeout(() => {
            navigate('/', { replace: true });
          }, 100);
        }
      } catch (err: any) {
        console.error('AuthCallback: Unexpected error:', err);
        if (isMounted) {
          setError(err.message || 'Authentication failed. Please try again.');
          setIsProcessing(false);
          sessionStorage.removeItem(processingKey);
          timeoutId = setTimeout(() => {
            if (isMounted) {
              navigate('/auth/login', { replace: true });
            }
          }, 3000);
        }
      }
    };

    handleAuthCallback();
    
    return () => {
      isMounted = false;
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      // Clear processing flag on cleanup
      sessionStorage.removeItem(processingKey);
    };
  }, [navigate, authLoading]); // Removed 'user' to prevent re-triggering when user state updates

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-primary/5 p-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-destructive">Authentication Error</CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => navigate('/auth/login')} className="w-full">
              Return to Login
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary/10 via-background to-primary/5 p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Completing Authentication</CardTitle>
          <CardDescription>Please wait while we sign you in...</CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </CardContent>
      </Card>
    </div>
  );
};

export default AuthCallback;

