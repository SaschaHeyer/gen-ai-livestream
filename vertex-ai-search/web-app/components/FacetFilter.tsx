import React from 'react';

interface FacetFilterProps {
    title: string;
    options: { label: string; value: string; count?: number }[];
    selectedValues: string[];
    onChange: (value: string) => void;
}

const FacetFilter: React.FC<FacetFilterProps> = ({ title, options, selectedValues, onChange }) => {
    return (
        <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-3">{title}</h3>
            <div className="space-y-2">
                {options.map((option) => (
                    <label key={option.value} className="flex items-center cursor-pointer group">
                        <input
                            type="checkbox"
                            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                            checked={selectedValues.includes(option.value)}
                            onChange={() => onChange(option.value)}
                        />
                        <span className="ml-2 text-sm text-gray-600 group-hover:text-gray-900">{option.label}</span>
                        {option.count !== undefined && (
                            <span className="ml-auto text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded-full">{option.count}</span>
                        )}
                    </label>
                ))}
            </div>
        </div>
    );
};

export default FacetFilter;
