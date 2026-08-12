/**
 * Authentication (ADR-0005) for the extension.
 *
 * The extension signs in through Firebase Auth (Google popup) like the
 * mobile app. Everything sits behind an [AuthGateway] port so tests and
 * local dev use the explicit mock; the ID token flows to the API client
 * as the bearer token.
 */
import { FirebaseApp, initializeApp } from 'firebase/app';
import {
  GoogleAuthProvider,
  User,
  getAuth,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
} from 'firebase/auth';

export interface AuthUser {
  uid: string;
  email: string | null;
  displayName: string | null;
}

export interface AuthGateway {
  currentUser(): Promise<AuthUser | null>;
  idToken(): Promise<string | null>;
  signInWithGoogle(): Promise<AuthUser>;
  signOut(): Promise<void>;
}

/** Firebase configuration; populated via build-time defines. */
export interface FirebaseConfig {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
}

/** Firebase-backed gateway using a Google popup sign-in. */
export class FirebaseAuthGateway implements AuthGateway {
  private readonly app: FirebaseApp;
  private readonly auth: ReturnType<typeof getAuth>;

  constructor(config: FirebaseConfig) {
    this.app = initializeApp(config);
    this.auth = getAuth(this.app);
  }

  async currentUser(): Promise<AuthUser | null> {
    return toAuthUser(this.auth.currentUser);
  }

  async idToken(): Promise<string | null> {
    const user = this.auth.currentUser;
    if (!user) return null;
    return user.getIdToken();
  }

  async signInWithGoogle(): Promise<AuthUser> {
    const provider = new GoogleAuthProvider();
    const result = await signInWithPopup(this.auth, provider);
    const user = toAuthUser(result.user);
    if (!user) throw new Error('auth.no_user: sign-in produced no user');
    return user;
  }

  async signOut(): Promise<void> {
    await firebaseSignOut(this.auth);
  }

  /** Subscribe to auth changes (used by the popup to refresh state). */
  onAuthStateChanged(listener: (user: AuthUser | null) => void): () => void {
    return onAuthStateChanged(this.auth, (user) => listener(toAuthUser(user)));
  }
}

function toAuthUser(user: User | null): AuthUser | null {
  if (!user) return null;
  return { uid: user.uid, email: user.email, displayName: user.displayName };
}

/** In-memory mock for tests and local development. */
export class MockAuthGateway implements AuthGateway {
  private user: AuthUser | null = null;
  signedOut = false;

  async currentUser(): Promise<AuthUser | null> {
    return this.user;
  }

  async idToken(): Promise<string | null> {
    return this.user ? `mock-token-${this.user.uid}` : null;
  }

  async signInWithGoogle(): Promise<AuthUser> {
    this.user = { uid: 'google-1', email: 'reader@example.com', displayName: 'Reader' };
    return this.user;
  }

  async signOut(): Promise<void> {
    this.signedOut = true;
    this.user = null;
  }
}
