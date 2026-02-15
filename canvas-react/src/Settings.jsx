import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Save, CheckCircle, XCircle, Clock, Settings as SettingsIcon } from 'lucide-react';
import { apiFetch } from './api';

const Settings = () => {
    const [settings, setSettings] = useState({
        course_id: '',
        course_name: '',
        canvas_api_url: '',
        last_sync: null,
    });
    const [availableCourses, setAvailableCourses] = useState([]);
    const [syncHistory, setSyncHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [syncing, setSyncing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [loadingCourses, setLoadingCourses] = useState(false);
    const [message, setMessage] = useState(null);
    const [manualCourseId, setManualCourseId] = useState('');

    // Fetch current settings
    const loadSettings = useCallback(async () => {
        try {
            const data = await apiFetch('/api/settings');
            setSettings(data);
            setManualCourseId(data.course_id || '');
        } catch (err) {
            console.error('Error loading settings:', err);
            setMessage({ type: 'error', text: 'Failed to load settings' });
        } finally {
            setLoading(false);
        }
    }, []);

    // Fetch sync status
    const loadSyncStatus = useCallback(async () => {
        try {
            const data = await apiFetch('/api/canvas/sync/status');
            setSyncHistory(data.history || []);
        } catch (err) {
            console.error('Error loading sync status:', err);
        }
    }, []);

    // Fetch available courses from Canvas
    const loadAvailableCourses = async () => {
        setLoadingCourses(true);
        try {
            const data = await apiFetch('/api/settings/courses');
            setAvailableCourses(data.courses || []);
        } catch (err) {
            console.error('Error loading courses:', err);
            setMessage({ type: 'error', text: err.message || 'Failed to connect to Canvas API' });
        } finally {
            setLoadingCourses(false);
        }
    };

    // Save settings
    const saveSettings = async () => {
        if (!manualCourseId.trim()) {
            setMessage({ type: 'error', text: 'Please enter a course ID' });
            return;
        }

        setSaving(true);
        try {
            await apiFetch('/api/settings', {
                method: 'PUT',
                body: JSON.stringify({ course_id: manualCourseId.trim() }),
            });
            setMessage({ type: 'success', text: 'Settings saved successfully' });
            loadSettings();
        } catch (err) {
            console.error('Error saving settings:', err);
            setMessage({ type: 'error', text: err.message || 'Failed to save settings' });
        } finally {
            setSaving(false);
        }
    };

    // Trigger sync
    const triggerSync = async () => {
        setSyncing(true);
        setMessage(null);
        try {
            const data = await apiFetch('/api/canvas/sync', {
                method: 'POST',
                body: JSON.stringify({ course_id: manualCourseId.trim() || null }),
            });
            setMessage({
                type: 'success',
                text: `Sync completed! ${data.stats?.assignments || 0} assignments, ${data.stats?.users || 0} users synced in ${data.duration_seconds}s`,
            });
            loadSettings();
            loadSyncStatus();
        } catch (err) {
            console.error('Error triggering sync:', err);
            setMessage({ type: 'error', text: err.message || 'Failed to trigger sync' });
        } finally {
            setSyncing(false);
        }
    };

    // Save and sync
    const saveAndSync = async () => {
        await saveSettings();
        await triggerSync();
    };

    useEffect(() => {
        loadSettings();
        loadSyncStatus();
    }, [loadSettings, loadSyncStatus]);

    // Clear message after 5 seconds
    useEffect(() => {
        if (message) {
            const timer = setTimeout(() => setMessage(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [message]);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen">
                <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
            </div>
        );
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            <div className="mb-8">
                <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                    <SettingsIcon className="w-6 h-6" />
                    Settings
                </h1>
                <p className="text-gray-600 mt-1">Configure your Canvas course and sync data</p>
            </div>

            {/* Message Banner */}
            {message && (
                <div
                    className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${message.type === 'success'
                            ? 'bg-green-50 text-green-800 border border-green-200'
                            : 'bg-red-50 text-red-800 border border-red-200'
                        }`}
                >
                    {message.type === 'success' ? (
                        <CheckCircle className="w-5 h-5" />
                    ) : (
                        <XCircle className="w-5 h-5" />
                    )}
                    {message.text}
                </div>
            )}

            {/* Course Configuration */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Course Configuration</h2>

                {/* Canvas API URL (read-only) */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Canvas API URL
                    </label>
                    <input
                        type="text"
                        value={settings.canvas_api_url || 'Not configured'}
                        disabled
                        className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-500"
                    />
                    <p className="text-xs text-gray-500 mt-1">
                        Set via CANVAS_API_URL environment variable
                    </p>
                </div>

                {/* Course ID Input */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Course ID
                    </label>
                    <div className="flex gap-2">
                        <input
                            type="text"
                            value={manualCourseId}
                            onChange={(e) => setManualCourseId(e.target.value)}
                            placeholder="Enter Canvas course ID"
                            className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        />
                        <button
                            onClick={loadAvailableCourses}
                            disabled={loadingCourses}
                            className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 flex items-center gap-2"
                        >
                            {loadingCourses ? (
                                <RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                                'Browse Courses'
                            )}
                        </button>
                    </div>
                </div>

                {/* Available Courses Dropdown */}
                {availableCourses.length > 0 && (
                    <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Available Courses
                        </label>
                        <select
                            onChange={(e) => setManualCourseId(e.target.value)}
                            value={manualCourseId}
                            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">Select a course...</option>
                            {availableCourses.map((course) => (
                                <option key={course.id} value={course.id}>
                                    {course.name} ({course.code || course.id})
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Current Course Info */}
                {settings.course_name && (
                    <div className="mb-4 p-3 bg-blue-50 rounded-md">
                        <p className="text-sm text-blue-800">
                            <strong>Current Course:</strong> {settings.course_name}
                        </p>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={saveSettings}
                        disabled={saving || !manualCourseId.trim()}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {saving ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        Save Settings
                    </button>
                    <button
                        onClick={saveAndSync}
                        disabled={syncing || saving || !manualCourseId.trim()}
                        className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {syncing ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                            <RefreshCw className="w-4 h-4" />
                        )}
                        Save & Sync Now
                    </button>
                </div>
            </div>

            {/* Sync Status */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Sync Status</h2>
                    <button
                        onClick={triggerSync}
                        disabled={syncing || !settings.course_id}
                        className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {syncing ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                            <RefreshCw className="w-4 h-4" />
                        )}
                        Sync Now
                    </button>
                </div>

                {settings.last_sync ? (
                    <div className="space-y-2">
                        <div className="flex items-center gap-2">
                            {settings.last_sync.status === 'success' ? (
                                <CheckCircle className="w-5 h-5 text-green-500" />
                            ) : settings.last_sync.status === 'in_progress' ? (
                                <RefreshCw className="w-5 h-5 text-blue-500 animate-spin" />
                            ) : (
                                <XCircle className="w-5 h-5 text-red-500" />
                            )}
                            <span className="font-medium capitalize">{settings.last_sync.status}</span>
                        </div>
                        {settings.last_sync.completed_at && (
                            <p className="text-sm text-gray-600 flex items-center gap-1">
                                <Clock className="w-4 h-4" />
                                Last synced: {new Date(settings.last_sync.completed_at).toLocaleString()}
                            </p>
                        )}
                        {settings.last_sync.message && (
                            <p className="text-sm text-gray-600">{settings.last_sync.message}</p>
                        )}
                        {settings.last_sync.assignments_count !== undefined && (
                            <p className="text-sm text-gray-600">
                                {settings.last_sync.assignments_count} assignments,{' '}
                                {settings.last_sync.submissions_count} submissions,{' '}
                                {settings.last_sync.users_count} users,{' '}
                                {settings.last_sync.groups_count} groups
                                {settings.last_sync.dropped_users_count > 0 && (
                                    <span className="text-orange-600">
                                        {' '}({settings.last_sync.dropped_users_count} dropped)
                                    </span>
                                )}
                            </p>
                        )}
                    </div>
                ) : (
                    <p className="text-gray-500">No sync history yet. Configure a course and sync to get started.</p>
                )}
            </div>

            {/* Sync History */}
            {syncHistory.length > 0 && (
                <div className="bg-white rounded-lg shadow-sm border p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">Sync History</h2>
                    <div className="space-y-3">
                        {syncHistory.map((sync, index) => (
                            <div
                                key={sync.id || index}
                                className="flex items-center justify-between p-3 bg-gray-50 rounded-md"
                            >
                                <div className="flex items-center gap-3">
                                    {sync.status === 'success' ? (
                                        <CheckCircle className="w-4 h-4 text-green-500" />
                                    ) : sync.status === 'in_progress' ? (
                                        <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
                                    ) : (
                                        <XCircle className="w-4 h-4 text-red-500" />
                                    )}
                                    <div>
                                        <p className="text-sm font-medium">
                                            Course {sync.course_id}
                                        </p>
                                        <p className="text-xs text-gray-500">
                                            {new Date(sync.started_at).toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                                {sync.status === 'success' && (
                                    <span className="text-xs text-gray-500">
                                        {sync.assignments_count} assignments, {sync.users_count} users
                                        {sync.dropped_users_count > 0 && (
                                            <span className="text-orange-600">
                                                {' '}({sync.dropped_users_count} dropped)
                                            </span>
                                        )}
                                    </span>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default Settings;
