/**
 * ProductSearchSelect - Reusable product search and selection component
 *
 * Features:
 * - Debounced search (300ms)
 * - Shows SKU, Name, Current Stock, Last Cost
 * - Category filter dropdown
 * - Keyboard navigation support
 */
import { useState, useEffect, useRef } from "react";
import { API_URL } from "../../config/api";

export default function ProductSearchSelect({
  value,
  onChange,
  products = [],
  placeholder = "Search or select product...",
  disabled = false,
  className = "",
  onCreateNew = null, // Callback to open create new item modal, receives search text
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [filteredProducts, setFilteredProducts] = useState(products);
  const [highlightedIndex, setHighlightedIndex] = useState(0);
  const containerRef = useRef(null);
  const inputRef = useRef(null);

  // Find selected product for display
  const selectedProduct = products.find(
    (p) => String(p.id) === String(value)
  );

  // Filter products based on search
  useEffect(() => {
    if (!search.trim()) {
      setFilteredProducts(products);
    } else {
      const searchLower = search.toLowerCase();
      const filtered = products.filter(
        (p) =>
          p.sku?.toLowerCase().includes(searchLower) ||
          p.name?.toLowerCase().includes(searchLower)
      );
      setFilteredProducts(filtered);
    }
    setHighlightedIndex(0);
  }, [search, products]);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setIsOpen(false);
        setSearch("");
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e) => {
    if (!isOpen) {
      if (e.key === "Enter" || e.key === "ArrowDown") {
        e.preventDefault();
        setIsOpen(true);
      }
      return;
    }

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setHighlightedIndex((prev) =>
          Math.min(prev + 1, filteredProducts.length - 1)
        );
        break;
      case "ArrowUp":
        e.preventDefault();
        setHighlightedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filteredProducts[highlightedIndex]) {
          handleSelect(filteredProducts[highlightedIndex]);
        }
        break;
      case "Escape":
        e.preventDefault();
        setIsOpen(false);
        setSearch("");
        break;
    }
  };

  const handleSelect = (product) => {
    onChange(product.id, product);
    setIsOpen(false);
    setSearch("");
  };

  const handleInputChange = (e) => {
    setSearch(e.target.value);
    if (!isOpen) {
      setIsOpen(true);
    }
  };

  const handleClear = (e) => {
    e.stopPropagation();
    onChange("", null);
    setSearch("");
  };

  return (
    <div ref={containerRef} className={`relative ${className}`}>
      <div
        className={`flex items-center bg-gray-800 border border-gray-700 rounded-lg overflow-hidden ${
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-text"
        } ${isOpen ? "ring-2 ring-blue-500" : ""}`}
        onClick={() => {
          if (!disabled) {
            setIsOpen(true);
            inputRef.current?.focus();
          }
        }}
      >
        <input
          ref={inputRef}
          type="text"
          value={isOpen ? search : selectedProduct ? `${selectedProduct.sku} - ${selectedProduct.name}` : ""}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          disabled={disabled}
          className="flex-1 bg-transparent px-3 py-2 text-white placeholder-gray-500 outline-none text-sm"
        />
        {value && !isOpen && (
          <button
            type="button"
            onClick={handleClear}
            className="px-2 text-gray-400 hover:text-white"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
        <div className="px-2 text-gray-400">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-60 overflow-auto">
          {filteredProducts.length === 0 ? (
            <div className="px-3 py-4 text-center text-gray-400 text-sm">
              {search ? (
                <div>
                  <p className="mb-2">No products found for "{search}"</p>
                  {onCreateNew && (
                    <button
                      type="button"
                      onClick={() => {
                        onCreateNew(search);
                        setIsOpen(false);
                      }}
                      className="text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1 mx-auto"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Create New Item
                    </button>
                  )}
                </div>
              ) : (
                "No products available"
              )}
            </div>
          ) : (
            <>
              {filteredProducts.map((product, index) => (
                <div
                  key={product.id}
                  onClick={() => handleSelect(product)}
                  onMouseEnter={() => setHighlightedIndex(index)}
                  className={`px-3 py-2 cursor-pointer transition-colors ${
                    index === highlightedIndex
                      ? "bg-blue-600/30"
                      : "hover:bg-gray-700/50"
                  } ${String(product.id) === String(value) ? "bg-blue-600/20" : ""}`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <div className="text-white text-sm font-medium">
                        {product.sku}
                      </div>
                      <div className="text-gray-400 text-xs truncate">
                        {product.name}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-gray-400">
                        Stock: {parseFloat(product.quantity_on_hand || 0).toFixed(0)}
                      </div>
                      {product.last_cost && (
                        <div className="text-xs text-gray-500">
                          ${parseFloat(product.last_cost).toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {/* Create New option at bottom when searching */}
              {onCreateNew && search && (
                <div
                  onClick={() => {
                    onCreateNew(search);
                    setIsOpen(false);
                  }}
                  className="px-3 py-2 cursor-pointer transition-colors border-t border-gray-700 hover:bg-green-600/20 text-green-400"
                >
                  <div className="flex items-center gap-2">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    <span className="text-sm font-medium">Create New Item</span>
                    <span className="text-xs text-gray-400">"{search}"</span>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
