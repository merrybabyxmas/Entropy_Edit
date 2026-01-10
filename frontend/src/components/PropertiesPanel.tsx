import React from 'react';
import { NeuSlider } from './NeuComponents';

const PropertiesPanel: React.FC = () => {
    return (
        <div className="flex flex-col gap-4 p-4 h-full">
            <h3 className="text-xs font-bold text-gray-500 mb-2">Properties</h3>

            <div className="space-y-4">
                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Sigma</span>
                        <span>3</span>
                    </div>
                    <NeuSlider defaultValue={30} />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Height</span>
                        <span>100</span>
                    </div>
                    <NeuSlider defaultValue={80} />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Position</span>
                        <span>180</span>
                    </div>
                    <NeuSlider defaultValue={60} />
                </div>

                 <div className="my-2 h-px bg-gray-300" />

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Transformer Perturbation</span>
                        <span>0</span>
                    </div>
                    <NeuSlider defaultValue={0} />
                </div>

                <div className="space-y-1">
                    <div className="flex justify-between text-xs text-text">
                        <span>Latent Jitter</span>
                        <span>100</span>
                    </div>
                    <NeuSlider defaultValue={90} />
                </div>
            </div>
        </div>
    );
};

export default PropertiesPanel;
