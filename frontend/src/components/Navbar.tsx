"use client";

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
}

export default function Navbar({ currentPage }: { currentPage?: string }) {
  const handleLogout = () => {
    localStorage.removeItem("bt_jwt");
    deleteCookie('bt_jwt');
    window.location.href = "/";
  };

  const navItems = [
    { label: "Dashboard", href: "/dashboard" },
    { label: "Order Flow", href: "/orderflow" },
  ];

  return (
    <nav className="bg-white border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <h1 className="text-xl font-bold text-primary-600">Bot Trader</h1>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              {navItems.map((item) => (
                <a
                  key={item.href}
                  href={item.href}
                  className={`inline-flex items-center px-1 pt-1 text-sm font-medium border-b-2 ${
                    currentPage === item.href
                      ? "border-primary-500 text-gray-900"
                      : "border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700"
                  }`}
                >
                  {item.label}
                </a>
              ))}
            </div>
          </div>
          <div className="flex items-center">
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-50 rounded-md"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

