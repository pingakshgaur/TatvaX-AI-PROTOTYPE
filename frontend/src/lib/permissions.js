// What the person using the app may do, from the permissions of their roles. A visitor without a
// profile yet has the base role's permissions. The server checks every action too; this only
// decides what to show.
export function can(app, user, permission) {
  const permissions = user?.permissions ?? app?.base_permissions ?? [];
  return permissions.includes(permission);
}
