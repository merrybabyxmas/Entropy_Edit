import React from 'react';
import { NeuSlider } from './NeuComponents';

export interface PropertyState {
    sigma: number;
    height: number;
    position: number;
    perturbation: number;
    jitter: number;
}

interface PropertiesPanelProps {
    values: PropertyState;
    onChange: (key: keyof PropertyState, value: number) => void;
}

const PropertiesPanel: React.FC<PropertiesPanelProps> = ({ values, onChange }) => {
    return (
        <div className="flex flex-col gap-4 p-4 h-full">
            <h3 className="text-xs font-bold text-gray-500 mb-2">Properties</h3>

            <div className="space-y-4">
                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Sigma</span>
                        <span>{values.sigma}</span>
                    </div>
                    <NeuSlider
                        min={0} max={100}
                        value={values.sigma}
                        onChange={(e) => onChange('sigma', Number(e.target.value))}
                    />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Height</span>
                        <span>{values.height}</span>
                    </div>
                    <NeuSlider
                         min={0} max={100}
                         value={values.height}
                         onChange={(e) => onChange('height', Number(e.target.value))}
                    />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Position</span>
                        <span>{values.position}</span>
                    </div>
                    <NeuSlider
                        min={0} max={360}
                        value={values.position}
                        onChange={(e) => onChange('position', Number(e.target.value))}
                    />
                </div>

                 <div className="my-2 h-px bg-gray-300" />

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Transformer Perturbation</span>
                        <span>{values.perturbation}</span>
                    </div>
                    <NeuSlider
                        min={0} max={100}
                        value={values.perturbation}
                        onChange={(e) => onChange('perturbation', Number(e.target.value))}
                    />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Latent Jitter</span>
                        <span>{values.jitter}</span>
                    </div>
                    <NeuSlider
                        min={0} max={100}
                        value={values.jitter}
                        onChange={(e) => onChange('jitter', Number(e.target.value))}
                    />
                </div>
            </div>
        </div>
    );
};

export default PropertiesPanel;
