import { Icon, ICredentialType, INodeProperties } from 'n8n-workflow';

export class SleeperCredential implements ICredentialType {
	name = 'sleeperCredential';
	displayName = 'Sleeper API';
	icon: Icon = 'file:sleeper_logo.svg';
	documentationUrl = 'https://docs.sleeper.com/';
	properties: INodeProperties[] = [
		{
			displayName: 'Sleeper Username',
			name: 'username',
			type: 'string',
			default: '',
			required: true,
			placeholder: 'your_sleeper_username',
			description: 'Your Sleeper username (no password required - Sleeper API is public)',
		},
	];
}