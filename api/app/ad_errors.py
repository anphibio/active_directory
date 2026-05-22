from fastapi import HTTPException, status


AD_PERMISSION_DENIED_DESCRIPTIONS = {
    "insufficientaccessrights",
    "unwillingtoperform",
}


def ad_modify_error(prefix: str, result: dict[str, object]) -> HTTPException:
    description = str(result.get("description") or "modifyFailed")
    message = str(result.get("message") or "")
    normalized_description = description.replace(" ", "").lower()
    normalized_message = message.lower()

    if (
        normalized_description in AD_PERMISSION_DENIED_DESCRIPTIONS
        or "insufficient access rights" in normalized_message
        or "access is denied" in normalized_message
    ):
        return HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Permissao negada pelo Active Directory. O operador ou a conta de servico "
                "nao possui privilegio para alterar este objeto. Isso normalmente ocorre "
                "quando o usuario alvo pertence a grupo protegido ou possui permissao superior."
            ),
        )

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"{prefix}: {description}",
    )
