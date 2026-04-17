import React, { useState, useRef, useEffect } from 'react';
import { CaretDown, CaretUp, Check, MagnifyingGlass } from '@phosphor-icons/react';
import './Select.css';

interface Option {
    value: string;
    label: React.ReactNode;
    searchLabel?: string; // Text to match against when searching
}

interface CustomSelectProps {
    options: Option[];
    value: string;
    onChange: (value: string) => void;
    placeholder?: string;
    className?: string;
    id?: string;
    required?: boolean;
    searchable?: boolean;
    searchPlaceholder?: string;
}

export const CustomSelect: React.FC<CustomSelectProps> = ({
    options,
    value,
    onChange,
    placeholder = 'Select',
    className = '',
    id,
    searchable = false,
    searchPlaceholder = 'Search...',
}) => {
    const [isOpen, setIsOpen] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const selectedOption = options.find((opt) => opt.value === value);

    // Filter options based on search term
    const filteredOptions = options.filter((opt) => {
        if (!searchTerm) return true;
        const term = searchTerm.toLowerCase();
        // Use searchLabel if provided, otherwise fallback to label (if string) or value
        const textToSearch = opt.searchLabel || (typeof opt.label === 'string' ? opt.label : opt.value);
        return textToSearch.toLowerCase().includes(term);
    });

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (
                containerRef.current &&
                !containerRef.current.contains(event.target as Node)
            ) {
                setIsOpen(false);
                setSearchTerm(''); // Reset search on close
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, []);

    // Focus search input when opening
    useEffect(() => {
        if (isOpen && searchable && searchInputRef.current) {
            searchInputRef.current.focus();
        }
    }, [isOpen, searchable]);

    const handleSelect = (optionValue: string) => {
        onChange(optionValue);
        setIsOpen(false);
        setSearchTerm('');
    };

    return (
        <div
            className={`custom-select-container ${className}`}
            ref={containerRef}
            id={id}
        >
            <div
                className={`custom-select-trigger ${isOpen ? 'open' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                tabIndex={0}
            >
                <span className={`custom-select-value ${!selectedOption ? 'placeholder' : ''}`}>
                    {selectedOption ? selectedOption.label : placeholder}
                </span>
                {isOpen ? (
                    <CaretUp size={14} weight="bold" className="custom-select-arrow" />
                ) : (
                    <CaretDown size={14} weight="bold" className="custom-select-arrow" />
                )}
            </div>

            {isOpen && (
                <div className="custom-select-options">
                    {searchable && (
                        <div className="custom-select-search">
                            <div className="search-input-wrapper">
                                <MagnifyingGlass size={16} className="search-icon" />
                                <input
                                    ref={searchInputRef}
                                    type="text"
                                    className="search-input"
                                    placeholder={searchPlaceholder}
                                    value={searchTerm}
                                    onChange={(e) => setSearchTerm(e.target.value)}
                                    onClick={(e) => e.stopPropagation()} // Prevent closing when clicking input
                                />
                            </div>
                        </div>
                    )}

                    <div className="custom-select-list">
                        {filteredOptions.length > 0 ? (
                            filteredOptions.map((option) => (
                                <div
                                    key={option.value}
                                    className={`custom-select-option ${option.value === value ? 'selected' : ''
                                        }`}
                                    onClick={() => handleSelect(option.value)}
                                >
                                    <span className="option-label">{option.label}</span>
                                    {option.value === value && (
                                        <Check size={14} weight="bold" className="option-check" />
                                    )}
                                </div>
                            ))
                        ) : (
                            <div className="custom-select-empty">No results found</div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
};
