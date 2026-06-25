import React, { useState, useEffect } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert, Dimensions } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

export default function ApiKeySettings({ onKeySaved }) {
  const [apiKey, setApiKey] = useState('');

  useEffect(() => {
    const loadKey = async () => {
      const savedKey = await AsyncStorage.getItem('user_gemini_key');
      if (savedKey) setApiKey(savedKey);
    };
    loadKey();
  }, []);

  const saveKeyToDevice = async () => {
    const trimmedKey = apiKey.trim();
    if (!trimmedKey) {
      Alert.alert('Error', 'Please enter a valid API key.');
      return;
    }
    try {
      await AsyncStorage.setItem('user_gemini_key', trimmedKey);
      // Explicitly tell App.js to update state and switch screens instantly
      if (onKeySaved) {
        onKeySaved(trimmedKey);
      } else {
        Alert.alert('Success', 'Gemini API key saved securely on this device.');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to save the key locally.');
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.headerTitle}>ZELTA SIGHT</Text>
        <Text style={styles.headerSubtitle}>CONFIGURATION PORTAL</Text>
        
        <Text style={styles.label}>ENTER GEMINI API TOKEN</Text>
        <TextInput
          style={styles.input}
          placeholder="AIzaSy..."
          placeholderTextColor="#555"
          value={apiKey}
          onChangeText={setApiKey}
          secureTextEntry={true}
          autoCapitalize="none"
          autoCorrect={false}
        />
        <Button title="SAVE ENCRYPTED KEY" onPress={saveKeyToDevice} color="#00b386" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#0a0a0f', padding: 24 },
  card: { width: '100%', maxWidth: 400, backgroundColor: '#11111a', padding: 25, borderRadius: 6, borderWidth: 1, borderColor: '#1a1b26' },
  headerTitle: { fontSize: 20, fontWeight: '800', color: '#fffffe', letterSpacing: 2, textAlign: 'center' },
  headerSubtitle: { fontSize: 9, fontWeight: '600', color: '#00b386', letterSpacing: 1, marginTop: 4, marginBottom: 25, textAlign: 'center' },
  label: { fontSize: 10, color: '#72757e', fontWeight: '700', letterSpacing: 1, marginBottom: 8 },
  input: { backgroundColor: '#0a0a0f', borderWidth: 1, borderColor: '#2e2f3e', borderRadius: 4, padding: 12, marginBottom: 20, color: '#fffffe', fontSize: 13 }
});