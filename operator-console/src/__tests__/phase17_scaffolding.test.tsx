import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { LoginPage } from '../pages/LoginPage';
import { Layout } from '../components/Layout';
import { PrivateRoute } from '../components/PrivateRoute';
import { useAuthStore } from '../store/authStore';
import apiClient from '../api/client';

vi.mock('../api/client');

describe('Phase 17: Frontend Scaffolding, Auth & Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.getState().logout();
  });

  it('renders login page with form elements and accessibility labels', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /Sign In to ClassAware/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeInTheDocument();
  });

  it('handles successful login and saves token to auth store', async () => {
    const mockedPost = vi.mocked(apiClient.post).mockResolvedValueOnce({
      data: {
        access_token: 'fake-jwt-token-xyz',
        role: 'teacher',
        token_type: 'bearer',
      },
    });

    render(
      <MemoryRouter initialEntries={['/login']}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<div>Dashboard Protected Area</div>} />
        </Routes>
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Username/i), {
      target: { value: 'teacher_1' },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'secret123' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith('/auth/login', {
        username: 'teacher_1',
        password: 'secret123',
      });
      expect(useAuthStore.getState().token).toBe('fake-jwt-token-xyz');
      expect(useAuthStore.getState().role).toBe('teacher');
      expect(useAuthStore.getState().username).toBe('teacher_1');
    });
  });

  it('displays error message on invalid credentials', async () => {
    vi.mocked(apiClient.post).mockRejectedValueOnce({
      response: { data: { detail: 'Incorrect username or password' } },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    fireEvent.change(screen.getByLabelText(/Username/i), {
      target: { value: 'baduser' },
    });
    fireEvent.change(screen.getByLabelText(/Password/i), {
      target: { value: 'wrongpass' },
    });
    fireEvent.click(screen.getByRole('button', { name: /Sign In/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/Incorrect username or password/i);
    });
  });

  it('PrivateRoute redirects unauthenticated user to /login', () => {
    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div>Login Page Screen</div>} />
          <Route element={<PrivateRoute />}>
            <Route path="/protected" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page Screen')).toBeInTheDocument();
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument();
  });

  it('PrivateRoute allows authenticated user to access protected routes', () => {
    useAuthStore.getState().login('valid-token', 'admin', 'admin_user');

    render(
      <MemoryRouter initialEntries={['/protected']}>
        <Routes>
          <Route path="/login" element={<div>Login Page Screen</div>} />
          <Route element={<PrivateRoute />}>
            <Route path="/protected" element={<div>Protected Content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Protected Content')).toBeInTheDocument();
  });

  it('Layout renders sidebar with navigation and header with user profile', () => {
    useAuthStore.getState().login('valid-token', 'teacher', 'prof_smith');

    render(
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<div>Child Page Body</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('ClassAware')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Live Monitor/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Alert Center/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Reports/i })).toBeInTheDocument();
    expect(screen.getByText('prof_smith')).toBeInTheDocument();
    expect(screen.getByText('teacher')).toBeInTheDocument();
    expect(screen.getByText('Child Page Body')).toBeInTheDocument();
  });
});
