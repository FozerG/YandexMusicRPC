#define ScriptVersion "0.1"
[Setup]
AppName=YandexMusicRPC
AppPublisher=FozerG
AppVersion={#ScriptVersion}
DefaultDirName={pf}\YandexMusicRPC
DefaultGroupName=YandexMusicRPC
OutputDir=dist
AppId=YandexMusicRPC
OutputBaseFilename=YandexMusicRPC_Installer_{#ScriptVersion}
Compression=lzma
SolidCompression=yes
DisableDirPage=yes       
DisableProgramGroupPage=yes
ShowLanguageDialog=no
SetupIconFile=assets\YMRPC_ico.ico
WizardImageFile=assets\YMRPC_large_bmp.bmp
WizardSmallImageFile=assets\YMRPC_bmp.bmp
WizardImageAlphaFormat=defined
PrivilegesRequired=admin
UninstallDisplayIcon={app}\YandexMusicRPC.exe
Uninstallable=yes  
AllowRootDirectory=no
AlwaysRestart=no 
MinVersion=10.0.17763

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
english.RunDescription=Run YandexMusicRPC
english.CreateDesktop=Create a desktop icon
english.AdditionalTasks=Additional tasks
russian.RunDescription=Запустить YandexMusicRPC
russian.CreateDesktop=Создать значок на рабочем столе
russian.AdditionalTasks=Дополнительные задачи

[Files]
Source: "dist\YandexMusicRPC-cli\YandexMusicRPC.exe"; DestDir: "{pf}\YandexMusicRPC"; Flags: ignoreversion
Source: "dist\YandexMusicRPC-cli\_internal\*"; DestDir: "{pf}\YandexMusicRPC\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\YandexMusicRPC"; Filename: "{pf}\YandexMusicRPC\YandexMusicRPC.exe"
Name: "{autodesktop}\YandexMusicRPC"; Filename: "{pf}\YandexMusicRPC\YandexMusicRPC.exe"; Tasks: desktopicon

[Code]
procedure DeleteStartupShortcut;
var
  StartupShortcut: string;
begin
  // Получаем путь к ярлыку в автозагрузке
  StartupShortcut := ExpandConstant('{userappdata}\Microsoft\Windows\Start Menu\Programs\Startup\YandexMusicRPC.lnk');
  
  // Проверяем, существует ли ярлык, и удаляем его, если он есть
  if FileExists(StartupShortcut) then
  begin
    DeleteFile(StartupShortcut);
  end;
end;

procedure DeleteRegistryEntry;
var
  RunKey: string;
begin
  // Определяем путь к ключу реестра
  RunKey := 'Software\Microsoft\Windows\CurrentVersion\Run';

  // Проверяем, существует ли запись реестра, и удаляем её, если она есть
  if RegValueExists(HKEY_CURRENT_USER, RunKey, 'YandexMusicRPC') then
  begin
    RegDeleteValue(HKEY_CURRENT_USER, RunKey, 'YandexMusicRPC');
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  // Выполняем действия только после завершения удаления программы
  if CurUninstallStep = usPostUninstall then
  begin
    DeleteStartupShortcut;
    DeleteRegistryEntry;
  end;
end;

[Run]
Filename: "{pf}\YandexMusicRPC\YandexMusicRPC.exe"; Description: "{cm:RunDescription}"; Flags: nowait postinstall skipifsilent

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktop}"; GroupDescription: "{cm:AdditionalTasks}"

[UninstallDelete]
Type: files; Name: "{pf}\YandexMusicRPC\_internal\*"
Type: dirifempty; Name: "{pf}\YandexMusicRPC\_internal"
Type: files; Name: "{pf}\YandexMusicRPC\YandexMusicRPC.exe"
Type: dirifempty; Name: "{pf}\YandexMusicRPC"
