import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Clock, Users, Settings } from 'lucide-react';

const Navigation = () => {
    const location = useLocation();

    return (
        <nav className="bg-white shadow-sm border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between h-14">
                    <div className="flex">
                        <div className="hidden sm:flex sm:space-x-8">
                            <Link
                                to="/"
                                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${location.pathname === '/'
                                        ? 'border-blue-500 text-gray-900'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    }`}
                            >
                                <LayoutDashboard className="w-4 h-4 mr-2" />
                                Dashboard
                            </Link>

                            <Link
                                to="/late-days"
                                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${location.pathname === '/late-days'
                                        ? 'border-blue-500 text-gray-900'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    }`}
                            >
                                <Clock className="w-4 h-4 mr-2" />
                                Late Days
                            </Link>

                            <Link
                                to="/peer-reviews"
                                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${location.pathname === '/peer-reviews'
                                        ? 'border-blue-500 text-gray-900'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    }`}
                            >
                                <Users className="w-4 h-4 mr-2" />
                                Peer Reviews
                            </Link>

                            <Link
                                to="/settings"
                                className={`inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium ${location.pathname === '/settings'
                                        ? 'border-blue-500 text-gray-900'
                                        : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                                    }`}
                            >
                                <Settings className="w-4 h-4 mr-2" />
                                Settings
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </nav>
    );
};

export default Navigation;
