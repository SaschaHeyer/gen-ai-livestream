import React from 'react';

interface FacetFilterProps {
    title: string;
    options: { label: string; value: string; count?: number; children?: string[] }[];
    selectedValues: string[];
    onChange: (value: string) => void;
    collapsible?: boolean;
    defaultOpenCount?: number;
}

const FacetFilter: React.FC<FacetFilterProps> = ({ title, options, selectedValues, onChange, collapsible = false, defaultOpenCount = 6 }) => {
    const [showAll, setShowAll] = React.useState(false);
    const rendered = collapsible && !showAll ? options.slice(0, defaultOpenCount) : options;

    return (
        <div className="mb-6">
            <h3 className="font-serif font-bold mb-3 border-b border-gray-300 pb-1 uppercase text-[13px]">
                {title}
            </h3>
            <div className="space-y-2 font-mono text-sm">
                {rendered.map((option) => (
                    <label key={option.value} className="flex items-center gap-2 cursor-pointer group">
                        <input
                            type="checkbox"
                            className="accent-[var(--chronos-black)] w-4 h-4"
                            checked={selectedValues.includes(option.value)}
                            onChange={() => onChange(option.value)}
                        />
                        <span className="group-hover:text-[var(--chronos-accent)]">{option.label}</span>
                        {option.count !== undefined && (
                            <span className="ml-auto text-gray-400 text-xs bg-gray-200 px-2 py-0.5 rounded-full">
                                {option.count}
                            </span>
                        )}
                    </label>
                ))}
                {collapsible && options.length > defaultOpenCount && (
                    <button
                        className="text-xs font-mono text-[var(--chronos-accent)] hover:underline"
                        onClick={() => setShowAll(!showAll)}
                    >
                        {showAll ? 'Show less' : `Show all (${options.length})`}
                    </button>
                )}
            </div>
        </div>
    );
};

export default FacetFilter;
