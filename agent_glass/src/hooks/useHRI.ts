'use client';

import { useCallback } from 'react';

export function useHRI() {
  const speak = useCallback((text: string, isRobot: boolean = false) => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const utterance = new SpeechSynthesisUtterance(text);
    const voices = window.speechSynthesis.getVoices();

    if (isRobot) {
      // Find a more mechanical/lower voice for the robot
      utterance.pitch = 0.5;
      utterance.rate = 0.8;
      // Try to find a specific robotic sounding voice if available
      const robotVoice = voices.find(v => v.name.includes('Google') || v.name.includes('Mechanical'));
      if (robotVoice) utterance.voice = robotVoice;
    } else {
      // Natural voice for the human
      utterance.pitch = 1.0;
      utterance.rate = 1.0;
      const humanVoice = voices.find(v => v.name.includes('Samantha') || v.name.includes('Female'));
      if (humanVoice) utterance.voice = humanVoice;
    }

    window.speechSynthesis.speak(utterance);

    return new Promise((resolve) => {
      utterance.onend = resolve;
    });
  }, []);

  const cancel = useCallback(() => {
    if (typeof window !== 'undefined' && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
  }, []);

  return { speak, cancel };
}
