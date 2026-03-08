import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Save, CheckCircle, XCircle, Clock, Settings as SettingsIcon, User, Database } from 'lucide-react';
import { apiFetch } from './api';
import { formatDate, setTimezone } from './utils/dates';

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
    const [saving, setSaving] = useState(false);
    const [loadingCourses, setLoadingCourses] = useState(false);
    const [message, setMessage] = useState(null);
    const [manualCourseId, setManualCourseId] = useState('');
    const [timezone, setTimezoneState] = useState('');
    const [apiUser, setApiUser] = useState(null);
    const [penaltyTemplate, setPenaltyTemplate] = useState({ id: null, text: '' });
    const [nonPenaltyTemplate, setNonPenaltyTemplate] = useState({ id: null, text: '' });
    const [templateSaving, setTemplateSaving] = useState(false);
    const [templateMessage, setTemplateMessage] = useState(null);
    const [policySaving, setPolicySaving] = useState(false);
    const [policyMessage, setPolicyMessage] = useState(null);

    // Late Day Policy state
    const [assignmentGroups, setAssignmentGroups] = useState([]);
    const [policySettings, setPolicySettings] = useState({
        total_late_day_bank: 10,
        penalty_rate_per_day: 25,
        per_assignment_cap: 7,
        late_day_eligible_groups: [],
    });
    const [policySettingsLoaded, setPolicySettingsLoaded] = useState(false);

    // Fetch current settings
    const loadSettings = useCallback(async () => {
        try {
            const data = await apiFetch('/api/settings');
            setSettings(data);
            setManualCourseId(data.course_id || '');
            setTimezoneState(data.timezone || '');
            setTimezone(data.timezone || null);
            setPolicySettings({
                total_late_day_bank: data.total_late_day_bank ?? 10,
                penalty_rate_per_day: data.penalty_rate_per_day ?? 25,
                per_assignment_cap: data.per_assignment_cap ?? 7,
                late_day_eligible_groups: data.late_day_eligible_groups ?? [],
            });
            setPolicySettingsLoaded(true);
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
        setSaving(true);
        try {
            const body = { timezone: timezone };
            if (manualCourseId.trim()) {
                body.course_id = manualCourseId.trim();
            }
            body.total_late_day_bank = policySettings.total_late_day_bank;
            body.penalty_rate_per_day = policySettings.penalty_rate_per_day;
            body.per_assignment_cap = policySettings.per_assignment_cap;
            body.late_day_eligible_groups = policySettings.late_day_eligible_groups;
            await apiFetch('/api/settings', {
                method: 'PUT',
                body: JSON.stringify(body),
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

    // Save only the Late Day Policy fields (independent of course/timezone settings)
    const savePolicySettings = async () => {
        setPolicySaving(true);
        setPolicyMessage(null);
        try {
            await apiFetch('/api/settings', {
                method: 'PUT',
                body: JSON.stringify({
                    total_late_day_bank: policySettings.total_late_day_bank,
                    penalty_rate_per_day: policySettings.penalty_rate_per_day,
                    per_assignment_cap: policySettings.per_assignment_cap,
                    late_day_eligible_groups: policySettings.late_day_eligible_groups,
                }),
            });
            setPolicyMessage({ type: 'success', text: 'Policy settings saved. Reload the Late Days Tracking page to see updated calculations.' });
            loadSettings();
        } catch (err) {
            console.error('Error saving policy settings:', err);
            setPolicyMessage({ type: 'error', text: err.message || 'Failed to save policy settings' });
        } finally {
            setPolicySaving(false);
        }
    };

    // Fetch comment templates
    const loadTemplates = useCallback(async () => {
        try {
            const data = await apiFetch('/api/templates');
            const templates = data.templates || [];
            const penalty = templates.find(t => t.template_type === 'penalty');
            const nonPenalty = templates.find(t => t.template_type === 'non_penalty');
            if (penalty) {
                setPenaltyTemplate({ id: penalty.id, text: penalty.template_text });
            }
            if (nonPenalty) {
                setNonPenaltyTemplate({ id: nonPenalty.id, text: nonPenalty.template_text });
            }
        } catch (err) {
            console.error('Error loading templates:', err);
        }
    }, []);

    // Save comment templates
    const saveTemplates = async () => {
        setTemplateSaving(true);
        setTemplateMessage(null);
        try {
            await apiFetch(`/api/templates/${penaltyTemplate.id}`, {
                method: 'PUT',
                body: JSON.stringify({ template_text: penaltyTemplate.text }),
            });
            await apiFetch(`/api/templates/${nonPenaltyTemplate.id}`, {
                method: 'PUT',
                body: JSON.stringify({ template_text: nonPenaltyTemplate.text }),
            });
            setTemplateMessage({ type: 'success', text: 'Templates saved successfully' });
        } catch (err) {
            setTemplateMessage({ type: 'error', text: err.message || 'Failed to save templates' });
        } finally {
            setTemplateSaving(false);
        }
    };

    // Load assignment groups for the Late Day Policy section
    const loadAssignmentGroups = useCallback(async () => {
        if (!settings.course_id) return;
        try {
            const data = await apiFetch(`/api/canvas/assignment-groups/${settings.course_id}`);
            const groups = data.groups || [];
            setAssignmentGroups(groups);
        } catch (err) {
            console.error('Error loading assignment groups:', err);
        }
    }, [settings.course_id]);

    useEffect(() => { loadAssignmentGroups(); }, [loadAssignmentGroups]);

    // Auto-populate eligible groups ONLY when settings have loaded and confirmed empty
    useEffect(() => {
        if (policySettingsLoaded && assignmentGroups.length > 0) {
            setPolicySettings(prev =>
                prev.late_day_eligible_groups.length === 0
                    ? { ...prev, late_day_eligible_groups: assignmentGroups.map(g => g.id) }
                    : prev
            );
        }
    }, [policySettingsLoaded, assignmentGroups]);

    useEffect(() => {
        loadSettings();
        loadSyncStatus();
        loadTemplates();
        apiFetch('/api/settings/api-user')
            .then(data => setApiUser(data))
            .catch(() => setApiUser(null));
    }, [loadSettings, loadSyncStatus, loadTemplates]);

    // Auto-dismiss success messages after 5 seconds; errors persist until user acts
    useEffect(() => {
        if (message?.type === 'success') {
            const timer = setTimeout(() => setMessage(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [message]);

    useEffect(() => {
        if (templateMessage?.type === 'success') {
            const timer = setTimeout(() => setTemplateMessage(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [templateMessage]);

    useEffect(() => {
        if (policyMessage?.type === 'success') {
            const timer = setTimeout(() => setPolicyMessage(null), 5000);
            return () => clearTimeout(timer);
        }
    }, [policyMessage]);

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

            {/* Connection Info */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Connection</h2>
                <div className="space-y-3">
                    <div className="flex items-start gap-3">
                        <User className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-gray-700">API Token Owner</p>
                            {apiUser ? (
                                <p className="text-sm text-gray-600">
                                    {apiUser.name}{apiUser.login_id ? ` (${apiUser.login_id})` : ''}
                                </p>
                            ) : (
                                <p className="text-sm text-gray-400 italic">Unable to fetch</p>
                            )}
                        </div>
                    </div>
                    <div className="flex items-start gap-3">
                        <Database className="w-4 h-4 text-gray-400 mt-0.5 shrink-0" />
                        <div>
                            <p className="text-sm font-medium text-gray-700">Database Location</p>
                            <p className="text-sm text-gray-600 font-mono break-all">
                                {settings.data_path || '—'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

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
                                    {course.name}{course.term ? ` — ${course.term}` : ''} ({course.code || course.id})
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

                {/* Timezone Setting */}
                <div className="mb-4">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Display Timezone
                    </label>
                    <select
                        value={timezone}
                        onChange={(e) => setTimezoneState(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    >
                        <option value="">Browser local time</option>
                        <option value="UTC">UTC</option>
                        <option value="America/New_York">Eastern (ET)</option>
                        <option value="America/Chicago">Central (CT)</option>
                        <option value="America/Denver">Mountain (MT)</option>
                        <option value="America/Los_Angeles">Pacific (PT)</option>
                    </select>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={saveSettings}
                        disabled={saving}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                    >
                        {saving ? (
                            <RefreshCw className="w-4 h-4 animate-spin" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        Save Settings
                    </button>
                </div>
            </div>

            {/* Sync Status */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <div className="mb-4">
                    <h2 className="text-lg font-semibold text-gray-900">Sync Status</h2>
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
                                Last synced: {formatDate(settings.last_sync.completed_at)}
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
                                            {formatDate(sync.started_at)}
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

            {/* Late Day Policy */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Late Day Policy</h2>
                <p className="text-sm text-gray-600 mb-6">
                    Configure the semester bank system for late day tracking.
                </p>

                {/* Three integer fields in a grid */}
                <div className="grid grid-cols-3 gap-4 mb-6">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Total Late Day Bank
                        </label>
                        <input
                            type="number" min="0" max="365"
                            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            value={policySettings.total_late_day_bank}
                            onChange={e => setPolicySettings(prev => ({ ...prev, total_late_day_bank: parseInt(e.target.value, 10) || 0 }))}
                        />
                        <p className="text-xs text-gray-500 mt-1">Days per student per semester</p>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Penalty Rate (% per day)
                        </label>
                        <input
                            type="number" min="0" max="100"
                            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            value={policySettings.penalty_rate_per_day}
                            onChange={e => setPolicySettings(prev => ({ ...prev, penalty_rate_per_day: parseInt(e.target.value, 10) || 0 }))}
                        />
                        <p className="text-xs text-gray-500 mt-1">Applied to days beyond bank</p>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">
                            Per-Assignment Cap
                        </label>
                        <input
                            type="number" min="0" max="365"
                            className="w-full border rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            value={policySettings.per_assignment_cap}
                            onChange={e => setPolicySettings(prev => ({ ...prev, per_assignment_cap: parseInt(e.target.value, 10) || 0 }))}
                        />
                        <p className="text-xs text-gray-500 mt-1">Max bank days per assignment</p>
                    </div>
                </div>

                {/* Assignment group eligibility checkbox list */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                        Late Day Eligible Assignment Groups
                    </label>
                    <p className="text-xs text-gray-500 mb-3">
                        Assignments in these groups can use late days. Assignments in other groups are &quot;Not Accepted&quot; if submitted late.
                        Leave all unchecked to allow late days on all assignments.
                    </p>
                    {assignmentGroups.length === 0 ? (
                        <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                            <p className="text-sm text-amber-800">
                                {settings.course_id
                                    ? 'No assignment groups found in local database. Sync course data to load groups — this reads from the local cache and does not contact Canvas.'
                                    : 'Select a course in Course Configuration above, then sync course data to see assignment groups.'}
                            </p>
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-48 overflow-y-auto border rounded-lg p-3 bg-gray-50">
                            {assignmentGroups.map(group => (
                                <label key={group.id} className="flex items-center gap-2 cursor-pointer hover:bg-white rounded px-2 py-1">
                                    <input
                                        type="checkbox"
                                        className="rounded border-gray-300 text-blue-600"
                                        checked={policySettings.late_day_eligible_groups.includes(group.id)}
                                        onChange={() => {
                                            setPolicySettings(prev => {
                                                const ids = prev.late_day_eligible_groups;
                                                const updated = ids.includes(group.id)
                                                    ? ids.filter(id => id !== group.id)
                                                    : [...ids, group.id];
                                                return { ...prev, late_day_eligible_groups: updated };
                                            });
                                        }}
                                    />
                                    <span className="text-sm text-gray-700">{group.name}</span>
                                </label>
                            ))}
                        </div>
                    )}
                </div>

                {/* Policy Message Banner */}
                {policyMessage && (
                    <div
                        className={`mb-4 p-3 rounded-lg flex items-center gap-2 text-sm ${policyMessage.type === 'success'
                                ? 'bg-green-50 text-green-800 border border-green-200'
                                : 'bg-red-50 text-red-800 border border-red-200'
                            }`}
                    >
                        {policyMessage.type === 'success' ? (
                            <CheckCircle className="w-4 h-4 shrink-0" />
                        ) : (
                            <XCircle className="w-4 h-4 shrink-0" />
                        )}
                        {policyMessage.text}
                    </div>
                )}

                {/* Save Policy Button */}
                <button
                    onClick={savePolicySettings}
                    disabled={policySaving}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                    {policySaving ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <Save className="w-4 h-4" />
                    )}
                    Save Policy Settings
                </button>
            </div>

            {/* Comment Templates */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Comment Templates</h2>
                <p className="text-sm text-gray-600 mb-4">
                    Configure the message templates used for late day comments. Use variables in curly braces for dynamic values.
                </p>

                {/* Template Message Banner */}
                {templateMessage && (
                    <div
                        className={`mb-6 p-4 rounded-lg flex items-center gap-2 ${templateMessage.type === 'success'
                                ? 'bg-green-50 text-green-800 border border-green-200'
                                : 'bg-red-50 text-red-800 border border-red-200'
                            }`}
                    >
                        {templateMessage.type === 'success' ? (
                            <CheckCircle className="w-5 h-5" />
                        ) : (
                            <XCircle className="w-5 h-5" />
                        )}
                        {templateMessage.text}
                    </div>
                )}

                {/* Variable Reference */}
                <div className="mb-6 p-3 bg-blue-50 rounded-md border border-blue-200">
                    <p className="text-sm font-medium text-blue-800 mb-1">Available Variables</p>
                    <div className="flex flex-wrap gap-2">
                        {['{days_late}', '{bank_days_used}', '{bank_remaining}', '{total_bank}', '{penalty_days}', '{penalty_percent}'].map(v => (
                            <code key={v} className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">{v}</code>
                        ))}
                    </div>
                </div>

                {/* Penalty Template */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Penalty Template
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                        Message for students who have exceeded their late day allowance
                    </p>
                    <textarea
                        value={penaltyTemplate.text}
                        onChange={(e) => setPenaltyTemplate(prev => ({ ...prev, text: e.target.value }))}
                        rows={8}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    />
                </div>

                {/* Non-Penalty Template */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                        Non-Penalty Template
                    </label>
                    <p className="text-xs text-gray-500 mb-2">
                        Message for students using late days within their allowance
                    </p>
                    <textarea
                        value={nonPenaltyTemplate.text}
                        onChange={(e) => setNonPenaltyTemplate(prev => ({ ...prev, text: e.target.value }))}
                        rows={8}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 font-mono text-sm"
                    />
                </div>

                {/* Save Button */}
                <button
                    onClick={saveTemplates}
                    disabled={templateSaving || !penaltyTemplate.id || !nonPenaltyTemplate.id}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
                >
                    {templateSaving ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                        <Save className="w-4 h-4" />
                    )}
                    Save Templates
                </button>
            </div>
        </div>
    );
};

export default Settings;
