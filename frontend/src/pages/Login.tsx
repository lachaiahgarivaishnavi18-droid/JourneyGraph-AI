import React, { useState } from 'react';
import { Network, ArrowRight, CircleHelp } from 'lucide-react';
import { api, post } from '../api';
import { Tag } from '../components/shared';
import type { Data } from '../components/shared';
export function Login({ onLogin }: {
    onLogin: (u: Data) => void;
}) {
    const [email, setEmail] = useState('admin@journeygraph.local'), [password, setPassword] = useState(''), [error, setError] = useState(''), [busy, setBusy] = useState(false), [register, setRegister] = useState(false);
    async function submit(e: React.FormEvent) { e.preventDefault(); setBusy(true); setError(''); try {
        if (register) {
            await post('/auth/register', { email, password });
            setRegister(false);
            setError('Viewer account created. Sign in to continue.');
        }
        else {
            const r = await post('/auth/login', { email, password });
            sessionStorage.setItem('jg-token', r.access_token);
            onLogin(r.user);
        }
    }
    catch (e) {
        setError((e as Error).message);
    }
    finally {
        setBusy(false);
    } }
    return <div className="login"><div className="login-story"><div className="brand"><div className="brand-icon"><Network /></div>JourneyGraph <b>AI</b></div><span className="eyebrow">EVERY INTERACTION HAS A STORY</span><h1>Connect the dots.<br />Understand the journey.</h1><p>Temporal knowledge graphs and coordinated intelligence, built around your customer evidence.</p><div className="login-graph">{['Discover', 'Explore', 'Consider', 'Purchase', 'Return'].map((s, i) => <React.Fragment key={s}><div style={{ animationDelay: i * .2 + 's' }}><span>{String(i + 1).padStart(2, '0')}</span>{s}</div>{i < 4 && <ArrowRight />}</React.Fragment>)}</div><span className="login-foot">Academic research platform · Private local workspace</span></div><form onSubmit={submit} className="login-form"><Tag tone="green">JOURNEY INTELLIGENCE</Tag><h2>{register ? 'Create viewer account' : 'Welcome to your workspace'}</h2><p>Sign in to explore customer journeys and their connections.</p><label>Email address<input type="email" value={email} onChange={e => setEmail(e.target.value)} required/></label><label>Password<input type="password" minLength={10} value={password} onChange={e => setPassword(e.target.value)} required placeholder="Your configured administrator password"/></label>{error && <div className="notice" role="alert">{error}</div>}<button className="primary" disabled={busy}>{busy ? 'Please wait…' : register ? 'Create account' : 'Sign in'}<ArrowRight size={17}/></button><button type="button" className="text-button" onClick={() => setRegister(!register)}>{register ? 'Back to sign in' : 'Create a viewer account'}</button><div className="login-note"><CircleHelp size={16}/><span>The first startup prints a generated administrator password. You can also set ADMIN_PASSWORD before starting the server.</span></div></form></div>;
}
