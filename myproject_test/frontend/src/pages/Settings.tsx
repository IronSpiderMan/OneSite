import React, { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { useForm, Controller } from 'react-hook-form';

const SettingsPage: React.FC = () => {
    const { t, i18n } = useTranslation();
    const { control, handleSubmit, setValue } = useForm();
    
    useEffect(() => {
        setValue('language', i18n.language);
        setValue('timezone', localStorage.getItem('timezone') || Intl.DateTimeFormat().resolvedOptions().timeZone);
    }, [i18n.language, setValue]);

    const onSubmit = (data: any) => {
        i18n.changeLanguage(data.language);
        localStorage.setItem('timezone', data.timezone);
        // We only save to local storage/i18n state, no API call needed.
        // Reload page to ensure all components pick up changes if necessary, 
        // though i18n is reactive. Timezone might need reload if used in initial state.
        window.location.reload(); 
    };

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">{t('common.settings')}</h1>
            
            <Card>
                <CardHeader>
                    <CardTitle>{t('common.settings')}</CardTitle>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-md">
                        <div className="space-y-2">
                            <Label>{t('common.language')}</Label>
                            <Controller
                                control={control}
                                name="language"
                                render={({ field }) => (
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Language" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="en">English</SelectItem>
                                            <SelectItem value="zh">中文</SelectItem>
                                        </SelectContent>
                                    </Select>
                                )}
                            />
                        </div>
                        
                        <div className="space-y-2">
                            <Label>{t('common.timezone')}</Label>
                            <Controller
                                control={control}
                                name="timezone"
                                render={({ field }) => (
                                    <Select onValueChange={field.onChange} value={field.value}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select Timezone" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="UTC">UTC</SelectItem>
                                            <SelectItem value="Asia/Shanghai">Asia/Shanghai</SelectItem>
                                            <SelectItem value="America/New_York">America/New_York</SelectItem>
                                            <SelectItem value="Europe/London">Europe/London</SelectItem>
                                            {/* Add more timezones as needed */}
                                        </SelectContent>
                                    </Select>
                                )}
                            />
                        </div>

                        <Button type="submit">{t('common.save')}</Button>
                    </form>
                </CardContent>
            </Card>
        </div>
    );
};

export default SettingsPage;